import logging
import os
import socket
from logging import getLogger
from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from github import Github
from pydantic import BaseModel, Field
import json
from typing import Optional, Dict, List
from helpers import review_pr, get_github_client
from webhook_manager import WebhookManager

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
    webhook_secret: Optional[str] = Field(None, description="Secret for GitHub webhook validation")
    webhook_url: Optional[str] = Field(None, description="URL for the webhook endpoint")

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
                github_token=os.environ["GITHUB_TOKEN"],
                port=int(os.environ.get("PORT", 8000)),
                webhook_secret=os.environ.get("WEBHOOK_SECRET"),
                webhook_url=os.environ.get("WEBHOOK_URL")
            )
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")

# Get webhook manager
def get_webhook_manager(config: Config = Depends(get_config)):
    github_client = get_github_client(config.github_token)
    webhook_url = config.webhook_url
    webhook_secret = config.webhook_secret or ""
    
    if not webhook_url:
        # Try to determine webhook URL from hostname
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        webhook_url = f"http://{ip}:{config.port}/webhook"
        logger.info(f"Auto-detected webhook URL: {webhook_url}")
    
    return WebhookManager(github_client, webhook_url, webhook_secret)

# GitHub webhook handler
@app.post("/webhook")
async def webhook(request: Request, config: Config = Depends(get_config)):
    # Get the raw request body
    body = await request.body()
    
    # Validate webhook signature if secret is configured
    if config.webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature:
            logger.warning("Missing webhook signature")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # TODO: Implement signature validation
    
    # Parse the webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Check event type
    event_type = request.headers.get("X-GitHub-Event")
    
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
            return {"status": "ignored", "reason": f"Ignored PR action: {action}"}
        
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
            github_client = get_github_client(config.github_token)
            result = review_pr(github_client, repo_name, pr_number)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error processing PR: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing PR: {str(e)}")
    
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
        github_client = get_github_client(config.github_token)
        result = review_pr(github_client, repo_full_name, pr_number)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error processing PR: {e}")
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
    logger.info(f"Starting PR Review Bot on port {config.port}")
    
    # Setup webhooks on startup if URL is provided
    if config.webhook_url:
        webhook_manager = get_webhook_manager(config)
        logger.info("Setting up webhooks for all repositories...")
        results = webhook_manager.setup_webhooks_for_all_repos()
        logger.info(f"Webhook setup completed for {len(results)} repositories")
    else:
        logger.warning("No webhook URL provided. Skipping automatic webhook setup.")
        logger.info("Use the /setup-webhooks endpoint after starting the server to set up webhooks.")
    
    uvicorn.run(app, host="0.0.0.0", port=config.port)