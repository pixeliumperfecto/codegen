import logging
import os
import subprocess
from logging import getLogger
from pyngrok import ngrok, conf, exception
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

class NgrokManager:
    """
    Manages ngrok tunnel for exposing the local server to the internet.
    """
    
    def __init__(self, port: int = 8000, auth_token: Optional[str] = None):
        """
        Initialize the ngrok manager.
        
        Args:
            port: Local port to expose (default: 8000)
            auth_token: Ngrok authentication token (optional)
        """
        self.port = port
        self.auth_token = auth_token
        self.tunnel = None
        self.public_url = None
        
    def _setup_auth_token(self) -> bool:
        """
        Set up the ngrok authentication token.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        if not self.auth_token:
            logger.warning("No ngrok authentication token provided")
            print("\n⚠️ No ngrok authentication token provided.")
            print("For better stability, set NGROK_AUTH_TOKEN in your .env file.")
            print("Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken")
            return False
            
        try:
            # First try to set via pyngrok
            conf.get_default().auth_token = self.auth_token
            logger.info("Ngrok authentication token set via pyngrok")
            
            # Also try to set via command line for persistence
            try:
                # Check if ngrok CLI is available
                subprocess.run(["ngrok", "--version"], capture_output=True, check=True)
                
                # Set the auth token via CLI
                result = subprocess.run(
                    ["ngrok", "config", "add-authtoken", self.auth_token],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Ngrok authentication token set via CLI")
                print("✅ Ngrok authentication token set successfully")
                return True
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                # CLI command failed, but pyngrok config should still work
                logger.warning(f"Could not set ngrok auth token via CLI: {e}")
                print("✅ Ngrok authentication token set via pyngrok only")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set ngrok authentication token: {e}")
            print(f"\n❌ Failed to set ngrok authentication token: {e}")
            return False
    
    def check_ngrok_installed(self) -> bool:
        """
        Check if ngrok is properly installed.
        
        Returns:
            bool: True if ngrok is installed, False otherwise
        """
        try:
            # Try to get ngrok version using pyngrok
            version = ngrok.get_ngrok_version()
            logger.info(f"Ngrok version: {version}")
            return True
        except exception.PyngrokNgrokError:
            logger.error("Ngrok binary not found")
            print("\n❌ Ngrok binary not found.")
            print("Please install ngrok with: pip install pyngrok")
            return False
        except Exception as e:
            logger.error(f"Error checking ngrok installation: {e}")
            print(f"\n❌ Error checking ngrok installation: {e}")
            return False
            
    def start_tunnel(self) -> Optional[str]:
        """
        Start an ngrok tunnel to expose the local server.
        
        Returns:
            Public URL for the tunnel, or None if failed
        """
        try:
            # Check if ngrok is installed
            if not self.check_ngrok_installed():
                return None
                
            # Set up authentication token
            self._setup_auth_token()
            
            # Start the tunnel
            logger.info(f"Starting ngrok tunnel for port {self.port}")
            print(f"\n🔄 Starting ngrok tunnel for port {self.port}...")
            
            # Connect with specific options for better stability
            self.tunnel = ngrok.connect(
                self.port, 
                "http",
                options={
                    "bind_tls": True,  # Ensure HTTPS
                    "inspect": False,  # Disable inspection for better performance
                }
            )
            self.public_url = self.tunnel.public_url
            
            # Log the public URL
            logger.info(f"Ngrok tunnel established: {self.public_url}")
            print(f"\n🚀 Ngrok tunnel established: {self.public_url}")
            
            # Return the webhook URL (public URL + /webhook)
            webhook_url = f"{self.public_url}/webhook"
            return webhook_url
            
        except exception.PyngrokNgrokAuthError as e:
            logger.error(f"Ngrok authentication error: {e}")
            print(f"\n❌ Ngrok authentication error: {e}")
            print("\nTo fix this issue:")
            print("1. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
            print("2. Add it to your .env file as NGROK_AUTH_TOKEN=\"your_token_here\"")
            print("3. Or run manually: ngrok config add-authtoken your_token_here")
            return None
            
        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {e}")
            print(f"\n❌ Failed to start ngrok tunnel: {e}")
            print("Make sure ngrok is installed and properly configured.")
            print("You can install ngrok with: pip install pyngrok")
            if not self.auth_token:
                print("\n⚠️ No ngrok authentication token provided.")
                print("For better stability, set NGROK_AUTH_TOKEN in your .env file.")
                print("Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken")
            return None
    
    def stop_tunnel(self):
        """
        Stop the ngrok tunnel.
        """
        if self.tunnel:
            try:
                logger.info("Stopping ngrok tunnel")
                ngrok.disconnect(self.tunnel.public_url)
                self.tunnel = None
                self.public_url = None
                logger.info("Ngrok tunnel stopped")
                print("\n✅ Ngrok tunnel stopped")
            except Exception as e:
                logger.error(f"Failed to stop ngrok tunnel: {e}")
                print(f"\n❌ Failed to stop ngrok tunnel: {e}")
    
    def get_webhook_url(self) -> Optional[str]:
        """
        Get the webhook URL for the ngrok tunnel.
        
        Returns:
            Webhook URL, or None if tunnel is not running
        """
        if self.public_url:
            return f"{self.public_url}/webhook"
        return None