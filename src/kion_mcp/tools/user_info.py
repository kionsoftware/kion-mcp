"""User info tools for Kion MCP Server."""

import logging
import json
from typing import Literal
from fastmcp import Context
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request


async def get_user_info_impl(
    ctx: Context,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager,
    user_type: Literal["me", "user", "user_group"],
    user_id: int = 0
) -> str:
    """Get user information by type and ID.
    
    Retrieves user information based on the specified type:
    - 'me': Returns current user's full information
    - 'user': Returns specific user information by ID
    - 'user_group': Returns user group information by ID
    
    Args:
        ctx: FastMCP context for the request
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        user_type: Type of user info to retrieve ("me", "user", or "user_group")
        user_id: The ID of the user or user group (required for "user" and "user_group" types)
        
    Returns:
        str: JSON string containing user information
        
    Raises:
        Exception: If the user information cannot be retrieved or authentication fails
    """
    logging.debug(f"Getting {user_type} info" + (f" for ID: {user_id}" if user_id != 0 else ""))
    
    # Map user types to API endpoints
    if user_type == "me":
        endpoint = "/v1/user/whoami"
    elif user_type == "user":
        if user_id == 0:
            raise ValueError("user_id is required when user_type is 'user'")
        endpoint = f"/v3/user/{user_id}"
    elif user_type == "user_group":
        if user_id == 0:
            raise ValueError("user_id is required when user_type is 'user_group'")
        endpoint = f"/v3/user-group/{user_id}"
    else:
        raise ValueError(f"Invalid user_type: {user_type}")
    
    response = await make_authenticated_request(
        mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
    )

    response_json = response.json()
    if user_type == "me":
        # This is a private endpoint so we're not returning the full user object
        response_json = {"user_id": response_json["data"]["id"]}

    logging.debug(f"Successfully retrieved {user_type} info for ID {user_id}")
    return json.dumps(response_json, indent=2)