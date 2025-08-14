"""Kion API client for MCP Server."""

import httpx
import logging
from typing import Dict, Any
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..exceptions import KionAPIError, AuthenticationError


class KionClient:
    """Client for interacting with Kion API."""
    
    def __init__(self, config: KionConfig):
        self.config = config
        self.auth_manager = AuthManager(config)
        self.client = httpx.AsyncClient(base_url=config.server_base_url)
        self._update_auth_header()
    
    def _update_auth_header(self) -> None:
        """Update the authorization header with current bearer token."""
        try:
            token = self.auth_manager.get_bearer_token()
            self.client.headers = {"Authorization": f"Bearer {token}"}
        except AuthenticationError as e:
            logging.error(f"Failed to get bearer token: {e}")
            # Don't raise here - let individual requests handle auth failures
    
    async def fetch_app_config(self) -> Dict[str, Any]:
        """Fetch app config from Kion API."""
        logging.info("Fetching app config")
        
        try:
            response = await self.client.get("/v3/app-config", timeout=20.0)
            
            if response.status_code == 401:
                logging.error("Unauthorized error fetching app config")
                if self.config.is_script_auth_mode():
                    # In script mode, try refreshing token and retry once
                    self._update_auth_header()
                    response = await self.client.get("/v3/app-config", timeout=20.0)

                else:
                    # Not in script mode - raise exception so server can fall back
                    logging.error("Authentication failed. Please update your bearer_token in kion_mcp_config.yaml")
                    raise AuthenticationError("Authentication failed - bearer token may be expired or invalid")
            
            if response.status_code != 200:
                raise KionAPIError(
                    f"Failed to fetch app config: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            app_config_data = response.json()
            app_config = app_config_data.get("data", {})
            
            logging.debug(f"Successfully fetched app config. Budget mode: {app_config.get('budget_mode', False)}")
            logging.debug(f"Enforce funding: {app_config.get('enforce_funding', False)}")
            logging.debug(f"Enforce funding sources: {app_config.get('enforce_funding_sources', False)}")
            
            return app_config
            
        except Exception as e:
            if not isinstance(e, KionAPIError):
                raise KionAPIError(f"Failed to fetch app config: {e}")
            raise
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
