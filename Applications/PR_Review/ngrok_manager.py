import logging
from logging import getLogger
from pyngrok import ngrok, conf
from typing import Optional

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
        
    def start_tunnel(self) -> Optional[str]:
        """
        Start an ngrok tunnel to expose the local server.
        
        Returns:
            Public URL for the tunnel, or None if failed
        """
        try:
            # Configure ngrok with auth token if provided
            if self.auth_token:
                logger.info("Setting ngrok authentication token")
                conf.get_default().auth_token = self.auth_token
                print("✅ Using provided ngrok authentication token")
            
            # Start the tunnel
            logger.info(f"Starting ngrok tunnel for port {self.port}")
            self.tunnel = ngrok.connect(self.port, "http")
            self.public_url = self.tunnel.public_url
            
            # Log the public URL
            logger.info(f"Ngrok tunnel established: {self.public_url}")
            print(f"\n🚀 Ngrok tunnel established: {self.public_url}")
            
            # Return the webhook URL (public URL + /webhook)
            webhook_url = f"{self.public_url}/webhook"
            return webhook_url
            
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
            except Exception as e:
                logger.error(f"Failed to stop ngrok tunnel: {e}")
    
    def get_webhook_url(self) -> Optional[str]:
        """
        Get the webhook URL for the ngrok tunnel.
        
        Returns:
            Webhook URL, or None if tunnel is not running
        """
        if self.public_url:
            return f"{self.public_url}/webhook"
        return None