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
        api_token: str, 
        account_id: str, 
        local_url: str = "http://localhost:8000/webhook",
        zone_id: Optional[str] = None,
        worker_route: Optional[str] = None
    ):
        """
        Initialize the Cloudflare manager.
        
        Args:
            api_token: Cloudflare API token with Workers permissions
            account_id: Cloudflare account ID
            local_url: URL of the local server to forward requests to
            zone_id: Optional Cloudflare zone ID for custom domain
            worker_route: Optional route pattern for the worker (e.g., "example.com/webhook/*")
        """
        self.api_token = api_token
        self.account_id = account_id
        self.local_url = local_url
        self.zone_id = zone_id
        self.worker_route = worker_route
        self.worker_name = "pr-review-bot"
        self.worker_url = None
    
    def create_worker(self) -> Optional[str]:
        """
        Create or update a Cloudflare Worker that forwards webhook requests.
        
        Returns:
            Public URL for the worker, or None if failed
        """
        try:
            # Worker script that forwards requests to the local server
            script = f"""
            addEventListener('fetch', event => {{
                event.respondWith(handleRequest(event.request))
            }})
            
            async function handleRequest(request) {{
                // Clone the request to forward it
                const requestClone = new Request(request)
                
                // Forward the request to the local server
                const url = "{self.local_url}"
                
                // Create a new request with the same method, headers, and body
                const newRequest = new Request(url, {{
                    method: requestClone.method,
                    headers: requestClone.headers,
                    body: requestClone.method !== 'GET' && requestClone.method !== 'HEAD' ? await requestClone.clone().arrayBuffer() : undefined
                }})
                
                try {{
                    // Forward the request and return the response
                    const response = await fetch(newRequest)
                    
                    // Clone the response to return it
                    const responseClone = new Response(await response.clone().arrayBuffer(), {{
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers
                    }})
                    
                    return responseClone
                }} catch (error) {{
                    // Return an error response if the request fails
                    return new Response(JSON.stringify({{ error: "Failed to forward request to local server" }}), {{
                        status: 500,
                        headers: {{ 'Content-Type': 'application/json' }}
                    }})
                }}
            }}
            """
            
            # API endpoint for creating/updating a worker
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts/{self.worker_name}"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/javascript"
            }
            
            # Create or update the worker
            response = requests.put(url, headers=headers, data=script)
            
            # Check if the request was successful
            if response.status_code in [200, 201]:
                logger.info(f"Worker created/updated successfully: {self.worker_name}")
                
                # Set the worker URL
                if self.zone_id and self.worker_route:
                    # If using a custom domain, create a route
                    self.create_worker_route()
                    self.worker_url = f"https://{self.worker_route.split('/')[0]}/webhook"
                else:
                    # If using workers.dev domain
                    self.worker_url = f"https://{self.worker_name}.{self.account_id}.workers.dev"
                
                logger.info(f"Worker URL: {self.worker_url}")
                print(f"\n🚀 Cloudflare Worker deployed: {self.worker_url}")
                
                return self.worker_url
            else:
                error_message = f"Failed to create/update worker: {response.status_code} - {response.text}"
                logger.error(error_message)
                print(f"\n❌ {error_message}")
                
                if response.status_code == 403:
                    print("Make sure your API token has the 'Workers Scripts:Edit' permission.")
                
                return None
                
        except Exception as e:
            logger.error(f"Error creating/updating worker: {e}")
            print(f"\n❌ Error creating/updating worker: {e}")
            return None
    
    def create_worker_route(self) -> bool:
        """
        Create a route for the worker on a custom domain.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.zone_id or not self.worker_route:
            logger.error("Zone ID and worker route are required for creating a route")
            return False
        
        try:
            # API endpoint for creating a route
            url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/workers/routes"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Data for the API request
            data = {
                "pattern": self.worker_route,
                "script": self.worker_name
            }
            
            # Create the route
            response = requests.post(url, headers=headers, json=data)
            
            # Check if the request was successful
            if response.status_code in [200, 201]:
                logger.info(f"Worker route created successfully: {self.worker_route}")
                print(f"✅ Worker route created: {self.worker_route}")
                return True
            else:
                error_message = f"Failed to create worker route: {response.status_code} - {response.text}"
                logger.error(error_message)
                print(f"❌ {error_message}")
                
                if response.status_code == 403:
                    print("Make sure your API token has the 'Workers Routes:Edit' permission.")
                
                return False
                
        except Exception as e:
            logger.error(f"Error creating worker route: {e}")
            print(f"❌ Error creating worker route: {e}")
            return False
    
    def get_webhook_url(self) -> Optional[str]:
        """
        Get the webhook URL for the Cloudflare Worker.
        
        Returns:
            Webhook URL, or None if worker is not deployed
        """
        return self.worker_url