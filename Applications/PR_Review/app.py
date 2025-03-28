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
from cloudflare_manager import CloudflareManager
from codegen.extensions.events.github import GitHub
from codegen.extensions.github.types.events.pull_request import PullRequestOpenedEvent
from codegen.git.repo_operator.repo_operator import RepoOperator
from codegen.configs.models.secrets import SecretsConfig
from codegen.git.schemas.repo_config import RepoConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="PR Review Bot", description="A bot that reviews PRs against documentation")

# Add GitHub event handler
github_handler = GitHub(app)

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
    use_cloudflare: bool = Field(False, description="Whether to use Cloudflare Workers for webhook forwarding")
    cloudflare_api_token: Optional[str] = Field(None, description="Cloudflare API token")
    cloudflare_account_id: Optional[str] = Field(None, description="Cloudflare account ID")
    cloudflare_zone_id: Optional[str] = Field(None, description="Cloudflare zone ID (optional)")
    cloudflare_worker_name: str = Field("pr-review-bot", description="Name for the Cloudflare Worker")
    cloudflare_worker_route: Optional[str] = Field(None, description="Route pattern for the Cloudflare Worker (optional)")


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
                ngrok_auth_token=os.environ.get("NGROK_AUTH_TOKEN"),
                use_cloudflare=os.environ.get("USE_CLOUDFLARE", "false").lower() == "true",
                cloudflare_api_token=os.environ.get("CLOUDFLARE_API_TOKEN"),
                cloudflare_account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID"),
                cloudflare_zone_id=os.environ.get("CLOUDFLARE_ZONE_ID"),
<<<<<< codegen-cloudflare-integration
                cloudflare_worker_name=os.environ.get("CLOUDFLARE_WORKER_NAME", "pr-review-bot"),

                cloudflare_worker_route=os.environ.get("CLOUDFLARE_WORKER_ROUTE")
            )
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")

# Global variables for URL management

ngrok_manager = None
cloudflare_manager = None
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
    
    # Use the override URL if available (from ngrok or Cloudflare)

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
            print("Consider enabling ngrok or Cloudflare in your environment.")

    else:
        # Check if webhook URL is accessible
        if not is_url_accessible(webhook_url):
            print(f"\n⚠️ WARNING: Webhook URL {webhook_url} does not appear to be publicly accessible.")
            print("GitHub webhooks require a publicly accessible URL.")
            print("Make sure your URL is correct and the server is running.\n")
    
    return WebhookManager(github_client, webhook_url)

# Verify Cloudflare signature
def verify_cloudflare_signature(request: Request, config: Config = Depends(get_config)):
    """Verify the signature from Cloudflare Worker"""
    # If not using Cloudflare, skip verification
    if not config.use_cloudflare:
        return True
    
    # Get the signature from the request headers
    signature = request.headers.get("X-Cloudflare-Signature")
    
    # If no signature is present, check if we're in development mode
    if not signature:
        logger.warning("No Cloudflare signature found in request")
        return True  # Allow in development mode
    
    # In production, you would verify the signature against a shared secret
    # For now, we'll just check if it exists
    return signature is not None

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

# Register GitHub event handlers
@github_handler.event("pull_request:opened")
def handle_pr_opened(event: PullRequestOpenedEvent):
    """Handle pull request opened events"""
    logger.info(f"Received pull request opened event: PR #{event.number}")
    
    try:
        # Get repository information
        repo_name = event.repository.full_name
        pr_number = event.number
        
        # Process the PR
        logger.info(f"Processing PR #{pr_number} in {repo_name}")
        github_client = Github(os.environ.get("GITHUB_TOKEN", ""))
        result = review_pr(github_client, repo_name, pr_number)
        logger.info(f"PR review completed for #{pr_number} in {repo_name}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error processing PR: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "error", 
            "message": f"Error processing PR: {str(e)}",
            "pr_number": event.number,
            "repo_name": event.repository.full_name
        }

@github_handler.event("pull_request:synchronize")
def handle_pr_synchronize(event: dict):
    """Handle pull request synchronize events (when PR is updated)"""
    logger.info(f"Received pull request synchronize event: PR #{event['number']}")
    
    try:
        # Get repository information
        repo_name = event['repository']['full_name']
        pr_number = event['number']
        
        # Process the PR
        logger.info(f"Processing updated PR #{pr_number} in {repo_name}")
        github_client = Github(os.environ.get("GITHUB_TOKEN", ""))
        result = review_pr(github_client, repo_name, pr_number)
        logger.info(f"PR review completed for updated #{pr_number} in {repo_name}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error processing updated PR: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "error", 
            "message": f"Error processing updated PR: {str(e)}",
            "pr_number": event['number'],
            "repo_name": event['repository']['full_name']
        }

@github_handler.event("repository:created")
def handle_repository_created(event: dict):
    """Handle repository creation events"""
    logger.info(f"Received repository created event")
    
    try:
        repo_name = event['repository']['full_name']
        logger.info(f"Setting up webhook for new repository: {repo_name}")
        
        config = get_config()
        webhook_manager = get_webhook_manager(config)
        success, message = webhook_manager.handle_repository_created(repo_name)
        
        logger.info(f"Webhook setup for new repository {repo_name}: {message}")
        return {"status": "success" if success else "error", "message": message}
    except Exception as e:
        logger.error(f"Error handling repository creation: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Error handling repository creation: {str(e)}"}

# GitHub webhook handler
@app.post("/webhook")
async def webhook(request: Request):
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
    
    # Process the event using GitHub handler
    try:
        return await github_handler.handle(payload, request)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        logger.error(traceback.format_exc())
        # Return a 200 response to GitHub to acknowledge receipt
        # This prevents GitHub from retrying the webhook
        return {
            "status": "error", 
            "message": f"Error processing webhook: {str(e)}"
        }

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

# Setup Cloudflare worker endpoint
@app.post("/setup-cloudflare")
async def setup_cloudflare(
    config: Config = Depends(get_config)
):
    """
    Set up a Cloudflare Worker for webhook forwarding.
    """
    global cloudflare_manager, webhook_url_override
    
    if not config.use_cloudflare:
        return {
            "status": "error",
            "message": "Cloudflare integration is not enabled. Set USE_CLOUDFLARE=true in your environment."
        }
    
    if not config.cloudflare_api_token or not config.cloudflare_account_id:
        return {
            "status": "error",
            "message": "Cloudflare API token and account ID are required."
        }
    
    # Create Cloudflare manager
    cloudflare_manager = CloudflareManager(
        cloudflare_api_token=config.cloudflare_api_token,
        cloudflare_account_id=config.cloudflare_account_id,
        cloudflare_zone_id=config.cloudflare_zone_id,
        worker_name=config.cloudflare_worker_name,
        worker_route=config.cloudflare_worker_route
    )
    
    # Generate a random webhook secret
    import secrets
    webhook_secret = secrets.token_hex(16)
    
    # Determine the target URL (local server)
    target_url = f"http://localhost:{config.port}/webhook"
    
    # Set up the Cloudflare Worker
    success, result = cloudflare_manager.setup_cloudflare_worker(target_url, webhook_secret)
    
    if success:
        # Set the webhook URL override to the Cloudflare Worker URL
        webhook_url_override = result
        
        # Update webhooks for all repositories
        webhook_manager = get_webhook_manager(config)
        webhook_results = webhook_manager.setup_webhooks_for_all_repos()
        
        return {
            "status": "success",
            "message": f"Cloudflare Worker set up successfully at {result}",
            "webhook_url": result,
            "webhook_results": webhook_results
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to set up Cloudflare Worker: {result}"
        }

# Test Cloudflare connection endpoint
@app.get("/test-cloudflare")
async def test_cloudflare(
    config: Config = Depends(get_config)
):
    """
    Test the connection to the Cloudflare Worker.
    """
    global cloudflare_manager
    
    if not config.use_cloudflare:
        return {
            "status": "error",
            "message": "Cloudflare integration is not enabled. Set USE_CLOUDFLARE=true in your environment."
        }
    
    if not cloudflare_manager:
        # Create Cloudflare manager
        cloudflare_manager = CloudflareManager(
            cloudflare_api_token=config.cloudflare_api_token,
            cloudflare_account_id=config.cloudflare_account_id,
            cloudflare_zone_id=config.cloudflare_zone_id,
            worker_name=config.cloudflare_worker_name,
            worker_route=config.cloudflare_worker_route
        )
    
    # Test the connection
    success, message = cloudflare_manager.test_worker_connection()
    
    return {
        "status": "success" if success else "error",
        "message": message,
        "worker_url": cloudflare_manager.get_worker_url()
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
    
    # Determine webhook URL
    if config.use_cloudflare and config.cloudflare_api_token and config.cloudflare_account_id:
        print("\n☁️ Setting up Cloudflare Worker for webhook forwarding...")
        
        # Create Cloudflare manager
        cloudflare_manager = CloudflareManager(
            cloudflare_api_token=config.cloudflare_api_token,
            cloudflare_account_id=config.cloudflare_account_id,
            cloudflare_zone_id=config.cloudflare_zone_id,
            worker_name=config.cloudflare_worker_name,
            worker_route=config.cloudflare_worker_route
        )
        
        # Generate a random webhook secret
        import secrets
        webhook_secret = secrets.token_hex(16)
        
        # Determine the target URL (local server)
        target_url = f"http://localhost:{config.port}/webhook"
        
        # Set up the Cloudflare Worker
        success, result = cloudflare_manager.setup_cloudflare_worker(target_url, webhook_secret)
        
        if success:
            print(f"\n🚀 Cloudflare Worker set up successfully at {result}")
            webhook_url_override = result
        else:
            print(f"\n⚠️ Failed to set up Cloudflare Worker: {result}")
            print("Falling back to ngrok or direct URL...")
    
    # Start ngrok if enabled and Cloudflare is not set up
    if config.use_ngrok and not webhook_url_override and not config.webhook_url:

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