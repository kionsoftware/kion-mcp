"""Entity management tools for Kion MCP Server."""

import logging
import json
from typing import Literal
from fastmcp import Context
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request


async def get_entity_by_id_impl(
    ctx: Context,
    entity_type: Literal["account", "ou", "project"],
    entity_id: int,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager
) -> str:
    """Get entity details by ID and type.
    
    Retrieves details for organizational units (OUs), projects, or accounts by their ID.
    
    Args:
        entity_type: Type of entity to retrieve ("account", "ou", or "project")
        entity_id: The ID of the entity to retrieve
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        
    Returns:
        str: JSON string containing entity details
        
    Raises:
        Exception: If the entity cannot be retrieved or authentication fails
    """
    logging.debug(f"Getting {entity_type} details for ID: {entity_id}")

    # Map entity types to API endpoints
    endpoint_map = {
        "account": f"/v3/account/{entity_id}",
        "ou": f"/v3/ou/{entity_id}",
        "project": f"/v3/project/{entity_id}"
    }
    
    endpoint = endpoint_map[entity_type]
    
    response = await make_authenticated_request(
        mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
    )

    logging.debug(f"Successfully retrieved {entity_type} {entity_id}")
    return json.dumps(response.json(), indent=2)