import logging
import requests
import json
import os
from typing import Optional, Dict, Any
from logging import getLogger

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

class CloudflareManager:
    """
    Manages Cloudflare Workers for exposing the local server to the internet.
    Creates a worker that forwards webhook requests to the local server.
    """
    
    def __init__(
        self, 
        cloudflare_api_token: str, 
        cloudflare_account_id: str,
        cloudflare_zone_id: Optional[str] = None,
        worker_name: str = "pr-review-bot",
        worker_route: Optional[str] = None
    ):
        """
        Initialize the Cloudflare manager.
        
        Args:
            cloudflare_api_token: Cloudflare API token with Workers and DNS permissions
            cloudflare_account_id: Cloudflare account ID
            cloudflare_zone_id: Optional Cloudflare zone ID (if using custom domain)
            worker_name: Name for the Cloudflare Worker
            worker_route: Optional route pattern for the worker (e.g., "example.com/webhook/*")
        """
        self.api_token = cloudflare_api_token
        self.account_id = cloudflare_account_id
        self.zone_id = cloudflare_zone_id
        self.worker_name = worker_name
        self.worker_route = worker_route
        self.worker_url = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Cloudflare API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def create_worker(self, target_url: str) -> Tuple[bool, str]:
        """
        Create or update a Cloudflare Worker that forwards webhook requests.
        
        Args:
            target_url: URL of the local server to forward requests to
            
        Returns:
            Tuple of (success, message or worker URL)
        """
        logger.info(f"Creating/updating Cloudflare Worker: {self.worker_name}")
        
        # Worker script that forwards requests to the target URL
        # and signs them with a shared secret for verification
        worker_script = f"""
        export default {{
          async fetch(request, env, ctx) {{
            // Clone the request so we can read the body
            const requestClone = request.clone();
            
            // Get the request body if it exists
            let body;
            try {{
              body = await requestClone.text();
            }} catch (e) {{
              body = "";
            }}
            
            // Get GitHub event type
            const eventType = request.headers.get('X-GitHub-Event') || 'unknown';
            
            // Create a new request to forward to the target
            const forwardRequest = new Request("{target_url}", {{
              method: request.method,
              headers: request.headers,
              body: body || undefined
            }});
            
            // Add a signature header for verification
            forwardRequest.headers.set('X-Cloudflare-Signature', env.WEBHOOK_SECRET || 'unsigned');
            
            // Forward the request to the target URL
            try {{
              const response = await fetch(forwardRequest);
              
              // Log the event
              console.log(`Forwarded ${{eventType}} event to {target_url}`);
              
              // Return the response from the target
              return response;
            }} catch (error) {{
              // If the target is unreachable, return a 502 Bad Gateway
              return new Response(`Error forwarding request: ${{error.message}}`, {{ status: 502 }});
            }}
          }}
        }};
        """
        
        # API endpoint for creating/updating a worker
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts/{self.worker_name}"
        
        try:
            # Upload the worker script
            response = requests.put(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/javascript"
                },
                data=worker_script
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Worker {self.worker_name} created/updated successfully")
                
                # Set the worker URL
                if self.worker_route:
                    self.worker_url = f"https://{self.worker_route}"
                else:
                    self.worker_url = f"https://{self.worker_name}.{self.account_id}.workers.dev/webhook"
                
                return True, self.worker_url
            else:
                error_msg = f"Failed to create/update worker: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error creating/updating Cloudflare Worker: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_worker_route(self) -> Tuple[bool, str]:
        """
        Create a route for the worker if a custom domain is specified.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.zone_id or not self.worker_route:
            return True, "No custom route specified, using workers.dev subdomain"
        
        logger.info(f"Creating route for worker: {self.worker_route}")
        
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/workers/routes"
        
        try:
            # Create the route
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={
                    "pattern": self.worker_route,
                    "script": self.worker_name
                }
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Route {self.worker_route} created successfully")
                return True, f"Route {self.worker_route} created successfully"
            else:
                error_msg = f"Failed to create route: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error creating Cloudflare Worker route: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def set_worker_secret(self, secret_name: str, secret_value: str) -> Tuple[bool, str]:
        """
        Set a secret for the worker.
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Setting secret {secret_name} for worker {self.worker_name}")
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts/{self.worker_name}/secrets"
        
        try:
            # Set the secret
            response = requests.put(
                url,
                headers=self._get_headers(),
                json={
                    "name": secret_name,
                    "text": secret_value
                }
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Secret {secret_name} set successfully")
                return True, f"Secret {secret_name} set successfully"
            else:
                error_msg = f"Failed to set secret: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error setting Cloudflare Worker secret: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def setup_cloudflare_worker(self, target_url: str, webhook_secret: Optional[str] = None) -> Tuple[bool, str]:
        """
        Set up a complete Cloudflare Worker configuration for webhook forwarding.
        
        Args:
            target_url: URL of the local server to forward requests to
            webhook_secret: Optional secret for signing webhook requests
            
        Returns:
            Tuple of (success, worker URL or error message)
        """
        # Step 1: Create/update the worker
        success, result = self.create_worker(target_url)
        if not success:
            return False, result
        
        # Step 2: Create a route if specified
        if self.zone_id and self.worker_route:
            route_success, route_result = self.create_worker_route()
            if not route_success:
                logger.warning(f"Failed to create route, but worker was created: {route_result}")
        
        # Step 3: Set webhook secret if provided
        if webhook_secret:
            secret_success, secret_result = self.set_worker_secret("WEBHOOK_SECRET", webhook_secret)
            if not secret_success:
                logger.warning(f"Failed to set webhook secret: {secret_result}")
        
        # Return the worker URL
        return True, self.worker_url
    
    def get_worker_url(self) -> Optional[str]:
        """
        Get the URL for the Cloudflare Worker.
        
        Returns:
            Worker URL or None if not set up
        """
        return self.worker_url
    
    def test_worker_connection(self) -> Tuple[bool, str]:
        """
        Test the connection to the Cloudflare Worker.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.worker_url:
            return False, "Worker URL not set"
        
        try:
            response = requests.get(self.worker_url)
            if response.status_code < 500:  # Allow 404 as the endpoint might only accept POST
                return True, f"Worker is accessible: {response.status_code}"
            else:
                return False, f"Worker returned error: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Error connecting to worker: {str(e)}"
