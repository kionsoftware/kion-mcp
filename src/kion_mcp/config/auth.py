"""Authentication management for Kion MCP Server."""

import os
import subprocess
import logging
from pathlib import Path
# No typing imports needed currently
from .settings import KionConfig
from ..exceptions import AuthenticationError
from ..interaction.elicitation import elicit_bearer_token


class AuthManager:
    """Manages authentication for Kion API."""
    
    def __init__(self, config: KionConfig):
        self.config = config
    
    def get_bearer_token(self, reload_config: bool = False) -> str:
        """Get bearer token from config or auth script.
        
        Args:
            reload_config: If True, reload config from file before getting token
        """
        logging.info("Getting bearer token")
        
        # Reload config from file if requested
        if reload_config:
            logging.info("Reloading config from file")
            try:
                self.config.reload()
            except Exception as e:
                logging.warning(f"Failed to reload config: {e}")
        
        # Check if auth script path is provided in config
        if self.config.auth_script_path:
            return self._get_token_from_script()
        
        # Fall back to bearer_token from config file
        if self.config.bearer_token:
            logging.info("Using bearer token from config file")
            return self.config.bearer_token
        
        raise AuthenticationError("No auth script path or bearer token found in config")
    
    def _get_token_from_script(self) -> str:
        """Get bearer token from auth script."""
        auth_script_path = self.config.auth_script_path
        
        try:
            # Support both absolute and relative paths
            if not os.path.isabs(auth_script_path):
                # Make relative to the root of the project
                auth_script_path = (Path(__file__).parent.parent.parent.parent / auth_script_path).resolve()
            
            logging.info(f"Executing auth script at: {auth_script_path}")
            result = subprocess.run([auth_script_path], capture_output=True, text=True, check=True)
            bearer_token = result.stdout.strip()
            logging.info(f"Successfully retrieved bearer token from auth script")
            return bearer_token
            
        except subprocess.CalledProcessError as e:
            raise AuthenticationError(f"Failed to get bearer token from auth script: {e}")
        except Exception as e:
            raise AuthenticationError(f"Error executing auth script: {e}")
    
    async def refresh_bearer_token_with_elicitation(self, ctx=None):
        """Try to refresh bearer token via elicitation if not in script mode."""
        if self.config.is_script_auth_mode():
            # In script mode, just use existing get_bearer_token
            token = self.get_bearer_token()
            return bool(token), token
        
        if ctx is None:
            return False, "No context available for token elicitation"
        
        # Try elicitation for new token
        logging.info("Attempting to elicit new bearer token")
        success, new_token = await elicit_bearer_token(ctx)
        new_token = new_token.strip()
        
        if success and new_token:
            # Update config file with new token
            try:
                self.config.bearer_token = new_token
                self.config.save()
                logging.info("Successfully updated config with new bearer token")
                return True, new_token
            except Exception as e:
                logging.error(f"Failed to update config with new token: {e}")
                return False, f"Failed to save new token: {e}"
        
        return False, "Token elicitation failed or was cancelled"