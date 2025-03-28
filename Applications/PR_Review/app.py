import logging
import os
from logging import getLogger
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from github import Github
from pydantic import BaseModel, Field
import json
from typing import Optional
from helpers import review_pr, get_github_client

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
                webhook_secret=os.environ.get("WEBHOOK_SECRET")
            )
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")

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
    
    # Check if this is a pull request event
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        logger.info(f"Ignoring non-PR event: {event_type}")
        return {"status": "ignored", "reason": "Not a pull request event"}
    
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

# Main entry point
if __name__ == "__main__":
    config = get_config()
    logger.info(f"Starting PR Review Bot on port {config.port}")
    uvicorn.run(app, host="0.0.0.0", port=config.port)