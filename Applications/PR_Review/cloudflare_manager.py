import logging
import requests
import json
import os
from typing import Optional, Dict, Any, Tuple, List
from logging import getLogger

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

class CloudflareManager:
    """
    Manages Cloudflare Workers for exposing the local server to the internet.
    Creates a worker that forwards webhook requests to the local server.
    Also manages KV storage for persistent data.
    """
    
    def __init__(
        self, 
        api_token: str, 
        account_id: str, 
        local_url: str = "http://localhost:8000/webhook",
        zone_id: Optional[str] = None,
        worker_route: Optional[str] = None,
        kv_namespace_id: Optional[str] = None
    ):
        """
        Initialize the Cloudflare manager.
        
        Args:
            api_token: Cloudflare API token with Workers permissions
            account_id: Cloudflare account ID
            local_url: URL of the local server to forward requests to
            zone_id: Optional Cloudflare zone ID for custom domain
            worker_route: Optional route pattern for the worker (e.g., "example.com/webhook/*")
            kv_namespace_id: Optional KV namespace ID for persistent storage
        """
        self.api_token = api_token
        self.account_id = account_id
        self.local_url = local_url
        self.zone_id = zone_id
        self.worker_route = worker_route
        self.worker_name = "pr-review-bot"
        self.worker_url = None
        self.kv_namespace_id = kv_namespace_id
        self.kv_namespace_name = "PR_REVIEW_BOT_KV"
    
    def create_worker(self) -> Optional[str]:
        """
        Create or update a Cloudflare Worker that forwards webhook requests.
        
        Returns:
            Public URL for the worker, or None if failed
        """
        try:
            # Check if KV namespace exists, create if not
            if not self.kv_namespace_id:
                self.create_kv_namespace()
            
            # Worker script that forwards requests to the local server
            # and uses KV for persistent storage
            script = f"""
            addEventListener('fetch', event => {{
                event.respondWith(handleRequest(event.request))
            }})
            
            async function handleRequest(request) {{
                // Clone the request to forward it
                const requestClone = new Request(request)
                
                // Get the GitHub event type
                const eventType = request.headers.get('X-GitHub-Event')
                
                // If this is a PR event, store some data in KV
                if (eventType === 'pull_request') {{
                    try {{
                        const body = await request.clone().json()
                        const prNumber = body.number
                        const repoName = body.repository.full_name
                        
                        // Store PR info in KV
                        await PR_REVIEW_BOT_KV.put(
                            `pr:${{repoName}}:${{prNumber}}`, 
                            JSON.stringify({{
                                updated_at: new Date().toISOString(),
                                action: body.action,
                                pr_url: body.pull_request.html_url
                            }}),
                            {{expirationTtl: 86400}} // Expire after 24 hours
                        )
                    }} catch (e) {{
                        // Ignore errors when storing in KV
                        console.error('Error storing PR data in KV:', e)
                    }}
                }}
                
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
                
                # Bind KV namespace to the worker if it exists
                if self.kv_namespace_id:
                    self.bind_kv_to_worker()
                
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
        
    def create_kv_namespace(self) -> bool:
        """
        Create a KV namespace for the worker.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # API endpoint for creating a KV namespace
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Data for the API request
            data = {
                "title": self.kv_namespace_name
            }
            
            # Create the KV namespace
            response = requests.post(url, headers=headers, json=data)
            
            # Check if the request was successful
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    self.kv_namespace_id = result["result"]["id"]
                    logger.info(f"KV namespace created successfully: {self.kv_namespace_name} (ID: {self.kv_namespace_id})")
                    print(f"✅ KV namespace created: {self.kv_namespace_name}")
                    return True
                else:
                    logger.error(f"Failed to create KV namespace: {result}")
                    print(f"❌ Failed to create KV namespace: {result}")
                    return False
            else:
                error_message = f"Failed to create KV namespace: {response.status_code} - {response.text}"
                logger.error(error_message)
                print(f"❌ {error_message}")
                
                if response.status_code == 403:
                    print("Make sure your API token has the 'Workers KV Storage:Edit' permission.")
                
                return False
                
        except Exception as e:
            logger.error(f"Error creating KV namespace: {e}")
            print(f"❌ Error creating KV namespace: {e}")
            return False
    
    def list_kv_namespaces(self) -> List[Dict[str, Any]]:
        """
        List all KV namespaces for the account.
        
        Returns:
            List of KV namespaces
        """
        try:
            # API endpoint for listing KV namespaces
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # List the KV namespaces
            response = requests.get(url, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    namespaces = result["result"]
                    logger.info(f"Found {len(namespaces)} KV namespaces")
                    
                    # Check if our namespace already exists
                    for namespace in namespaces:
                        if namespace["title"] == self.kv_namespace_name:
                            self.kv_namespace_id = namespace["id"]
                            logger.info(f"Found existing KV namespace: {self.kv_namespace_name} (ID: {self.kv_namespace_id})")
                            print(f"✅ Found existing KV namespace: {self.kv_namespace_name}")
                            break
                    
                    return namespaces
                else:
                    logger.error(f"Failed to list KV namespaces: {result}")
                    return []
            else:
                logger.error(f"Failed to list KV namespaces: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing KV namespaces: {e}")
            return []
    
    def bind_kv_to_worker(self) -> bool:
        """
        Bind the KV namespace to the worker.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.kv_namespace_id:
            logger.error("KV namespace ID is required for binding to worker")
            return False
        
        try:
            # API endpoint for binding KV to worker
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/workers/scripts/{self.worker_name}/bindings"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Data for the API request
            data = {
                "bindings": [
                    {
                        "type": "kv_namespace",
                        "name": "PR_REVIEW_BOT_KV",
                        "namespace_id": self.kv_namespace_id
                    }
                ]
            }
            
            # Bind the KV namespace to the worker
            response = requests.put(url, headers=headers, json=data)
            
            # Check if the request was successful
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    logger.info(f"KV namespace bound to worker successfully")
                    print(f"✅ KV namespace bound to worker")
                    return True
                else:
                    logger.error(f"Failed to bind KV namespace to worker: {result}")
                    print(f"❌ Failed to bind KV namespace to worker: {result}")
                    return False
            else:
                error_message = f"Failed to bind KV namespace to worker: {response.status_code} - {response.text}"
                logger.error(error_message)
                print(f"❌ {error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error binding KV namespace to worker: {e}")
            print(f"❌ Error binding KV namespace to worker: {e}")
            return False
    
    def write_kv_value(self, key: str, value: str, expiration_ttl: Optional[int] = None) -> bool:
        """
        Write a value to the KV namespace.
        
        Args:
            key: Key to write
            value: Value to write
            expiration_ttl: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.kv_namespace_id:
            logger.error("KV namespace ID is required for writing values")
            return False
        
        try:
            # API endpoint for writing a KV value
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{self.kv_namespace_id}/values/{key}"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Data for the API request
            data = {}
            if expiration_ttl:
                data["expiration_ttl"] = expiration_ttl
            
            # Write the value
            response = requests.put(url, headers=headers, data=value, params=data)
            
            # Check if the request was successful
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    logger.info(f"KV value written successfully: {key}")
                    return True
                else:
                    logger.error(f"Failed to write KV value: {result}")
                    return False
            else:
                logger.error(f"Failed to write KV value: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error writing KV value: {e}")
            return False
    
    def read_kv_value(self, key: str) -> Optional[str]:
        """
        Read a value from the KV namespace.
        
        Args:
            key: Key to read
            
        Returns:
            Value if successful, None otherwise
        """
        if not self.kv_namespace_id:
            logger.error("KV namespace ID is required for reading values")
            return None
        
        try:
            # API endpoint for reading a KV value
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{self.kv_namespace_id}/values/{key}"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}"
            }
            
            # Read the value
            response = requests.get(url, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.info(f"KV value not found: {key}")
                return None
            else:
                logger.error(f"Failed to read KV value: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading KV value: {e}")
            return None
    
    def list_kv_keys(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List keys in the KV namespace.
        
        Args:
            prefix: Optional prefix to filter keys
            
        Returns:
            List of keys
        """
        if not self.kv_namespace_id:
            logger.error("KV namespace ID is required for listing keys")
            return []
        
        try:
            # API endpoint for listing KV keys
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{self.kv_namespace_id}/keys"
            
            # Headers for the API request
            headers = {
                "Authorization": f"Bearer {self.api_token}"
            }
            
            # Parameters for the API request
            params = {}
            if prefix:
                params["prefix"] = prefix
            
            # List the keys
            response = requests.get(url, headers=headers, params=params)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    keys = result["result"]
                    logger.info(f"Found {len(keys)} KV keys")
                    return keys
                else:
                    logger.error(f"Failed to list KV keys: {result}")
                    return []
            else:
                logger.error(f"Failed to list KV keys: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing KV keys: {e}")
            return []