"""Main server entry point for Kion MCP Server."""

import httpx
import json
import logging
import re
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.openapi import OpenAPITool, HTTPRoute

from .server_management.tool_manager import configure_server_state
from .server_management.routes import KION_ROUTES
from .utils.dxt import is_dxt_mode
from .utils.spec_loader import load_openapi_spec
from .tools.custom_tools import register_custom_tools
from .constants.tools import *



# Configure logging based on execution mode
import sys

if is_dxt_mode():
    # DXT mode - log to stderr
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
else:
    # Standalone mode - log to file
    logging.basicConfig(
        filename='server_log.log', 
        filemode='w', 
        level=logging.INFO, 
        format='%(asctime)s %(levelname)s %(message)s'
    )



def customize_components(_: HTTPRoute, component: OpenAPITool) -> None:
    """Customize OpenAPI components before they are converted into tools."""
    # Remove the trailing "Responses:" section from the description
    pat = re.compile(
        r'''(?s)
        ^.*?\S
        (?=\s*\n\s*\*\*Responses:\*\*)
        ''',
        re.VERBOSE,
    )
    try:
        component.description = pat.search(component.description).group(0)
    except AttributeError:
        logging.warning(f"Failed to customize component description for `{component.name}` with description: `{component.description}`")

    component.output_schema = None

async def create_full_server_async() -> FastMCP:
    """Create the full Kion MCP server with async initialization."""
    # Use mutable container for config and auth_manager. This allows us to update them later via pass by reference.
    auth_state = {"config": None, "auth_manager": None}
    
    # Create HTTP client with placeholder - will be updated during configuration
    logging.debug("Creating http client with placeholder URL")
    client = httpx.AsyncClient(base_url="https://placeholder.com")

    # Load OpenAPI spec
    logging.debug("Loading OpenAPI spec")
    openapi_spec = load_openapi_spec()
    logging.debug("OpenAPI spec loaded successfully")

    # Create the MCP server with static routes
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Kion MCP Server",
        route_maps=KION_ROUTES,
        mcp_names=TOOL_NAME_MAPPING,
        mcp_component_fn=customize_components,
    )
    
    # Register custom tools with mutable container
    register_custom_tools(mcp, auth_state)
    
    # Set initial tool availability and apply description updates based on current state
    await configure_server_state(mcp, auth_state)
    
    return mcp


async def main():
    """Main entry point for the server."""
    logging.info("Starting Kion MCP Server")
    mcp = await create_full_server_async()
    await mcp.run_async()


def run():
    """Entry point for the console script."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run()