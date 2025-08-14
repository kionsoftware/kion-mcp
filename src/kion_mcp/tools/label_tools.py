"""Label-related tools for Kion MCP Server."""

import logging
import json
from fastmcp import Context
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request


async def get_label_key_id_impl(
    ctx: Context,
    label_id: int,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager
) -> str:
    """Get a label's key ID by label ID.
    
    Retrieves the key ID needed for tag filtering operations.
    
    Args:
        label_id: The ID of the label to get the key ID for
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        
    Returns:
        str: JSON string containing the key ID
        
    Raises:
        Exception: If the label key ID cannot be retrieved or authentication fails
    """
    logging.debug(f"Getting label key ID for label ID: {label_id}")
    response = await make_authenticated_request(
        mcp_http_client, "GET", f"/v1/app-label/{label_id}?includeDeleted=false", 
        config, auth_manager, ctx, timeout=20.0
    )

    logging.debug("Successfully retrieved label key ID")
    data = response.json()
    return json.dumps({"key_id": data["data"]["key_id"]})