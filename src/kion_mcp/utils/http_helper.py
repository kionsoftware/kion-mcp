"""
HTTP helper utilities for authenticated requests to Kion API.
"""

import logging
from pathlib import Path
from typing import Tuple
from importlib.metadata import version

import httpx

from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.dxt import is_dxt_mode


def get_auth_failure_message(config_path: str) -> str:
    """Get appropriate authentication failure message based on runtime mode."""
    if is_dxt_mode():
        return (
            "Authentication failed. Direct the user to double check their authentication or generate a new app API key since the user's may have just expired. "
            "The user is running this MCP Server as a dxt so their auth tokens are likely provided by a client side config (they're most likely using Claude Desktop so they can update their App API Key in the Claude Desktop \"Settings\" menu, then click \"Extensions\" on the sidebar, then click \"Configure\" on Kion MCP Server, and then by replacing the Bearer Token field in that menu with a new App API Key from Kion). "
            f"If they used the config file instead they can update that at {config_path} with a new bearer token instead. "
            "Inform the user of this and try to guide them through updating their auth info. Once the user says they've fixed the problem get them to restart the app you are running in which should update the auth info."
        )
    else:
        return (
            f"Authentication failed. Please refresh your bearer token or check your authentication script. "
            f"Config file: {config_path}"
        )


def build_standard_headers(bearer_token: str) -> dict:
    """Build standard HTTP headers with Authorization and metadata.
    
    Args:
        bearer_token: The bearer token for authentication
        
    Returns:
        dict: HTTP headers with Authorization and Kion metadata
    """
    try:
        kion_version = version("kion-mcp-server")
    except Exception:
        kion_version = "0.0.0"  # Fallback version

    return {
        "Authorization": f"Bearer {bearer_token}",
        "kion-source": "kion-mcp",
        "kion-source-version": kion_version
    }


async def refresh_authentication(
    config: KionConfig,
    auth_manager: AuthManager, 
    http_client: httpx.AsyncClient,
    context
) -> Tuple[bool, str]:
    """
    Attempt to refresh the authentication token using all available methods.
    
    Args:
        config: Kion configuration object
        auth_manager: Authentication manager instance
        http_client: HTTP client instance to update headers
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    logging.info("Attempting token refresh")
    
    # Try to refresh token with elicitation if not in script mode
    success, new_token_or_msg = await auth_manager.refresh_bearer_token_with_elicitation(context)
    
    if success:
        http_client.headers = build_standard_headers(new_token_or_msg)
        logging.info("Token refreshed successfully via elicitation")
        return True, ""
    
    # If elicitation failed, try to reload config directly
    logging.info("Elicitation failed, attempting config reload")
    
    try:
        new_token = auth_manager.get_bearer_token(reload_config=True)
        http_client.headers = build_standard_headers(new_token)
        logging.info("Token refreshed successfully via config reload")
        return True, ""
    except Exception as e:
        config_path = str(Path(config._config_path or "kion_mcp_config.yaml").resolve())
        error_msg = f"Failed to reload authentication config from {config_path}. Error: {str(e)}"
        return False, error_msg


async def make_authenticated_request(
    http_client: httpx.AsyncClient,
    method: str,
    url: str,
    config: KionConfig,
    auth_manager: AuthManager,
    context,
    json=None,
    timeout=20
):
    """
    Make an authenticated HTTP request with automatic token refresh on 401 errors.
    
    Args:
        http_client: HTTP client instance (httpx.AsyncClient)
        method: HTTP method ('GET', 'POST', etc.)
        url: Request URL
        config: Kion configuration object
        auth_manager: Authentication manager instance
        context: FastMCP context for elicitation
        json: JSON request body (optional)
        timeout: Request timeout in seconds
    
    Returns:
        Response object from the HTTP client
        
    Raises:
        Exception: On authentication failure or other HTTP errors
    """
    # Make initial request
    response = await http_client.request(method, url, json=json, timeout=timeout)
    
    if response.status_code == 200:
        logging.debug(f"Successful {method} request to {url}")
        return response
    elif response.status_code == 401:
        logging.debug("Unauthorized error, attempting token refresh")

        # Try to refresh authentication
        refresh_success, error_msg = await refresh_authentication(config, auth_manager, http_client, context)
        
        if refresh_success:
            # Retry the request with refreshed token
            logging.debug("Retrying request with refreshed token")
            retry_response = await http_client.request(method, url, json=json, timeout=timeout)
            
            if retry_response.status_code == 200:
                logging.debug(f"Successful {method} request to {url} after token refresh")
                return retry_response
            elif retry_response.status_code == 401:
                config_path = str(Path(config._config_path or "kion_mcp_config.yaml").resolve())
                raise Exception(get_auth_failure_message(config_path))
            else:
                raise Exception(f"Request failed after token refresh: {retry_response.status_code} {retry_response.text}")
        else:
            # Refresh failed
            raise Exception(error_msg)
    else:
        raise Exception(f"Request failed: {response.status_code} {response.text}")