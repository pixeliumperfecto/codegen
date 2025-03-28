import logging
import os
import socket
import requests
import traceback
from logging import getLogger
from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from github import Github
from pydantic import BaseModel, Field
import json
from typing import Optional, Dict, List
from helpers import review_pr, get_github_client
from webhook_manager import WebhookManager
from ngrok_manager import NgrokManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="PR Review Bot", description="A bot that reviews PRs against documentation")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration model
class Config(BaseModel):
    github_token: str = Field(..., description="GitHub Personal Access Token")
    port: int = Field(8000, description="Port for the local server")
    webhook_url: Optional[str] = Field(None, description="URL for the webhook endpoint")
    use_ngrok: bool = Field(True, description="Whether to use ngrok for exposing the server")
    ngrok_auth_token: Optional[str] = Field(None, description="Ngrok authentication token")

# Load configuration
def get_config():
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config_data = json.load(f)
                return Config(**config_data)
        else:
            # Use environment variables as fallback
            return Config(
                github_token=os.environ.get("GITHUB_TOKEN", ""),
                port=int(os.environ.get("PORT", 8000)),
                webhook_url=os.environ.get("WEBHOOK_URL"),
                use_ngrok=os.environ.get("USE_NGROK", "true").lower() == "true",
                ngrok_auth_token=os.environ.get("NGROK_AUTH_TOKEN")
            )
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")

# Global variables for ngrok
ngrok_manager = None
webhook_url_override = None

def is_url_accessible(url: str) -> bool:
    """Check if a URL is publicly accessible"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code < 400
    except:
        return False

# Get webhook manager
def get_webhook_manager(config: Config = Depends(get_config)):
    global webhook_url_override
    
    if not config.github_token:
        print("ERROR: GitHub token not provided. Please set the GITHUB_TOKEN environment variable.")
        print("Make sure your token has 'admin:repo_hook' scope to create webhooks.")
        raise HTTPException(status_code=500, detail="GitHub token not provided")
        
    github_client = get_github_client(config.github_token)
    
    # Use the override URL if available (from ngrok)
    webhook_url = webhook_url_override or config.webhook_url
    
    if not webhook_url:
        # Try to determine webhook URL from hostname
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        webhook_url = f"http://{ip}:{config.port}/webhook"
        logger.info(f"Auto-detected webhook URL: {webhook_url}")
        
        # Check if using localhost or private IP
        if ip.startswith(("127.", "10.", "172.", "192.168.")):
            print("\n⚠️ WARNING: Using a local IP address for webhook URL.")
            print("GitHub webhooks require a publicly accessible URL.")
            print("Consider enabling ngrok by setting USE_NGROK=true in your environment.")
    else:
        # Check if webhook URL is accessible
        if not is_url_accessible(webhook_url):
            print(f"\n⚠️ WARNING: Webhook URL {webhook_url} does not appear to be publicly accessible.")
            print("GitHub webhooks require a publicly accessible URL.")
            print("Make sure your URL is correct and the server is running.\n")
    
    return WebhookManager(github_client, webhook_url)

# Exception handler for all unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"An unexpected error occurred: {str(exc)}",
            "type": type(exc).__name__
        }
    )

# GitHub webhook handler
@app.post("/webhook")
async def webhook(request: Request, config: Config = Depends(get_config)):
    # Get the raw request body
    body = await request.body()
    
    # Parse the webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Check event type
    event_type = request.headers.get("X-GitHub-Event")
    logger.info(f"Received webhook event: {event_type}")
    
    # Handle repository creation event
    if event_type == "repository":
        action = payload.get("action")
        if action == "created":
            repo_name = payload.get("repository", {}).get("full_name")
            if repo_name:
                webhook_manager = get_webhook_manager(config)
                success, message = webhook_manager.handle_repository_created(repo_name)
                return {"status": "success" if success else "error", "message": message}
    
    # Handle pull request event
    if event_type == "pull_request":
        # Check if this is a relevant action
        action = payload.get("action")
        if action not in ["opened", "synchronize", "reopened"]:
            logger.info(f"Ignoring PR action: {action}")
            return {"status": "ignored", "reason": f"Ignoring PR action: {action}"}
        
        # Get repository information
        repo_name = payload.get("repository", {}).get("full_name")
        if not repo_name:
            logger.error("Missing repository information")
            raise HTTPException(status_code=400, detail="Missing repository information")
        
        # Get PR information
        pr_number = payload.get("pull_request", {}).get("number")
        if not pr_number:
            logger.error("Missing PR number")
            raise HTTPException(status_code=400, detail="Missing PR number")
        
        # Process the PR
        try:
            logger.info(f"Processing PR #{pr_number} in {repo_name}")
            github_client = get_github_client(config.github_token)
            result = review_pr(github_client, repo_name, pr_number)
            logger.info(f"PR review completed for #{pr_number} in {repo_name}")
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error processing PR: {e}")
            logger.error(traceback.format_exc())
            # Return a 200 response to GitHub to acknowledge receipt
            # This prevents GitHub from retrying the webhook
            return {
                "status": "error", 
                "message": f"Error processing PR: {str(e)}",
                "pr_number": pr_number,
                "repo_name": repo_name
            }
    
    # Return for other event types
    return {"status": "ignored", "reason": f"Ignored event type: {event_type}"}

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Manual review endpoint
@app.post("/review/{repo_owner}/{repo_name}/{pr_number}")
async def manual_review(
    repo_owner: str, 
    repo_name: str, 
    pr_number: int, 
    config: Config = Depends(get_config)
):
    repo_full_name = f"{repo_owner}/{repo_name}"
    
    # Process the PR
    try:
        logger.info(f"Manual review requested for PR #{pr_number} in {repo_full_name}")
        github_client = get_github_client(config.github_token)
        result = review_pr(github_client, repo_full_name, pr_number)
        logger.info(f"Manual PR review completed for #{pr_number} in {repo_full_name}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error processing PR: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing PR: {str(e)}")

# Setup webhooks endpoint
@app.post("/setup-webhooks")
async def setup_webhooks(
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_config)
):
    """
    Set up webhooks for all repositories accessible by the GitHub token.
    This runs in the background to avoid timeout issues with many repositories.
    """
    webhook_manager = get_webhook_manager(config)
    
    # Run webhook setup in background
    background_tasks.add_task(webhook_manager.setup_webhooks_for_all_repos)
    
    return {
        "status": "started",
        "message": "Webhook setup started in background. Check logs for progress."
    }

# Get webhook status endpoint
@app.get("/webhook-status")
async def webhook_status(
    config: Config = Depends(get_config)
):
    """
    Get the status of webhooks for all repositories.
    """
    webhook_manager = get_webhook_manager(config)
    repos = webhook_manager.get_all_repositories()
    
    status = {}
    for repo in repos:
        hook = webhook_manager.find_pr_review_webhook(repo)
        if hook:
            status[repo.full_name] = {
                "has_webhook": True,
                "webhook_url": hook.config.get("url"),
                "events": hook.events,
                "active": hook.active
            }
        else:
            status[repo.full_name] = {
                "has_webhook": False
            }
    
    return {
        "webhook_url": webhook_manager.webhook_url,
        "repositories": status
    }

# Main entry point
if __name__ == "__main__":
    config = get_config()
    
    # Check GitHub token
    if not config.github_token:
        print("\n❌ ERROR: GitHub token not provided.")
        print("Please set the GITHUB_TOKEN environment variable.")
        print("Example: export GITHUB_TOKEN=ghp_your_token_here")
        print("Make sure your token has 'admin:repo_hook' scope to create webhooks.\n")
        exit(1)
    
    print("\n🤖 Starting PR Review Bot")
    
    # Start ngrok if enabled
    if config.use_ngrok and not config.webhook_url:
        print("\n🔄 Starting ngrok tunnel...")
        ngrok_manager = NgrokManager(config.port, auth_token=config.ngrok_auth_token)
        webhook_url_override = ngrok_manager.start_tunnel()
        
        if not webhook_url_override:
            print("\n⚠️ WARNING: Failed to start ngrok tunnel.")
            print("The bot will continue to run, but webhooks may not work correctly.")
            print("Consider setting WEBHOOK_URL manually or fixing ngrok installation.\n")
    
    print(f"\n🌐 Server will run on: http://0.0.0.0:{config.port}")
    
    # Setup webhooks on startup
    if webhook_url_override or config.webhook_url:
        webhook_manager = get_webhook_manager(config)
        print("\n🔗 Setting up webhooks for all repositories...")
        results = webhook_manager.setup_webhooks_for_all_repos()
        print(f"\n✅ Webhook setup completed for {len(results)} repositories")
    else:
        print("\n⚠️ No webhook URL available. Skipping webhook setup.")
        print("The bot will still respond to manual requests, but won't receive GitHub events.")
    
    # Start the server
    print("\n🚀 Starting server...")
    
    # Register shutdown event to stop ngrok
    def shutdown_event():
        if ngrok_manager:
            print("\n🛑 Stopping ngrok tunnel...")
            ngrok_manager.stop_tunnel()
    
    # Start uvicorn with shutdown event
    uvicorn.run(app, host="0.0.0.0", port=config.port)