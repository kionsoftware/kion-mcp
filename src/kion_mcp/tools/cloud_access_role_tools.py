"""Cloud Access Role tools for Kion MCP Server."""

import logging
import json
from typing import Literal
from fastmcp import Context
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request


async def get_cloud_access_roles_on_entity_impl(
    ctx: Context,
    entity_type: Literal["project", "ou"],
    entity_id: int,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager
) -> str:
    """Get cloud access roles on an entity by ID and type.
    
    Retrieves cloud access roles for projects or OUs by their ID.
    For projects, returns both local and inherited cloud access roles.
    For OUs, returns OU-specific cloud access roles.
    
    Args:
        entity_type: Type of entity ("project" or "ou")
        entity_id: The ID of the entity to retrieve cloud access roles for
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        
    Returns:
        str: JSON string containing cloud access roles
        
    Raises:
        Exception: If the cloud access roles cannot be retrieved or authentication fails
    """
    logging.debug(f"Getting cloud access roles for {entity_type} ID: {entity_id}")
    
    # Map entity types to API endpoints
    endpoint_map = {
        "project": f"/v3/project/{entity_id}/cloud-access-role",
        "ou": f"/v3/ou/{entity_id}/ou-cloud-access-role"
    }
    
    endpoint = endpoint_map[entity_type]
    
    response = await make_authenticated_request(
        mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
    )

    logging.debug(f"Successfully retrieved cloud access roles for {entity_type} {entity_id}")
    return json.dumps(response.json(), indent=2)


async def get_cloud_access_role_details_impl(
    ctx: Context,
    role_type: Literal["project", "ou"],
    role_id: int,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager
) -> str:
    """Get detailed cloud access role information by ID and type.
    
    Retrieves detailed information for project or OU cloud access roles including
    embedded IAM policies, Azure roles, GCP roles, accounts, and user/group mappings.
    
    Args:
        role_type: Type of cloud access role ("project" or "ou")
        role_id: The ID of the cloud access role to retrieve details for
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        
    Returns:
        str: JSON string containing detailed cloud access role information
        
    Raises:
        Exception: If the cloud access role details cannot be retrieved or authentication fails
    """
    logging.debug(f"Getting {role_type} cloud access role details for ID: {role_id}")

    # Map role types to API endpoints
    endpoint_map = {
        "project": f"/v3/project-cloud-access-role/{role_id}",
        "ou": f"/v3/ou-cloud-access-role/{role_id}"
    }
    
    endpoint = endpoint_map[role_type]
    
    response = await make_authenticated_request(
        mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
    )

    logging.debug(f"Successfully retrieved {role_type} cloud access role details for ID {role_id}")
    return json.dumps(response.json(), indent=2)