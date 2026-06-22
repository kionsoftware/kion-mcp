"""Tool management and server state configuration for Kion MCP Server."""

import logging
from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..middleware.auth import AuthenticationMiddleware
from ..middleware.financial import FinancialOperationMiddleware
from ..clients.kion_client import KionClient
from ..config.settings import save_app_config_cache, load_app_config_cache
from ..constants.tools import *
from ..constants.tools import CONFIG_MODE_TOOLS
from ..exceptions import ConfigurationError
from ..utils.route_generator import generate_tool_description_append
from ..utils.http_helper import build_standard_headers


def needs_configuration() -> bool:
    """Check if server needs to be in configuration mode."""
    try:
        config = KionConfig.load()
        return config.needs_configuration()
    except ConfigurationError:
        # No config file exists, create placeholder and enter config mode
        try:
            config = KionConfig()
            config.create_placeholder_config()
            logging.info("Created placeholder config file for setup")
        except Exception as e:
            logging.error(f"Failed to create placeholder config: {e}")
        return True


def enable_tools(mcp: FastMCP, tool_names: list[str]) -> None:
    """
    Enable a list of tools by their names.

    Args:
        mcp: The FastMCP server instance
        tool_names: List of tool names to enable
    """
    names = set(tool_names)
    if names:
        # FastMCP 3.x: toggling is done at the server level by name; unknown
        # names are ignored silently.
        mcp.enable(names=names)
        logging.debug(f"Enabled tools: {sorted(names)}")


def disable_tools(mcp: FastMCP, tool_names: list[str]) -> None:
    """
    Disable a list of tools by their names.

    Args:
        mcp: The FastMCP server instance
        tool_names: List of tool names to disable
    """
    names = set(tool_names)
    if names:
        mcp.disable(names=names)
        logging.debug(f"Disabled tools: {sorted(names)}")


def enable_tool(mcp: FastMCP, tool_name: str) -> bool:
    """
    Enable a single tool by name.

    Args:
        mcp: The FastMCP server instance
        tool_name: Name of the tool to enable

    Returns:
        True (the request is dispatched to the server; unknown names are no-ops)
    """
    enable_tools(mcp, [tool_name])
    return True


def disable_tool(mcp: FastMCP, tool_name: str) -> bool:
    """
    Disable a single tool by name.

    Args:
        mcp: The FastMCP server instance
        tool_name: Name of the tool to disable

    Returns:
        True (the request is dispatched to the server; unknown names are no-ops)
    """
    disable_tools(mcp, [tool_name])
    return True


async def load_app_config_for_tools() -> dict:
    """
    Load app config for tool configuration.
    
    Returns:
        dict: App configuration data
        
    Raises:
        Exception: If app config cannot be loaded from any source
    """
    config = KionConfig.load()
    kion_client = KionClient(config)
    
    try:
        # Try fresh app config first
        app_config = await kion_client.fetch_app_config()
        save_app_config_cache(app_config)
        logging.info("Using fresh app config for tool configuration")
        return app_config
    except Exception as e:
        # Fallback to cache
        logging.error(f"API fetch failed: {e}, trying cache")
        app_config = load_app_config_cache()
        if app_config is None:
            # No cache available - raise error to trigger fallback
            logging.error("No fresh config and no cache available")
            raise Exception("Unable to load app config from API or cache")
        else:
            logging.info("Using cached app config for tool configuration")
            return app_config
    finally:
        await kion_client.close()


def disable_tools_based_on_config(mcp: FastMCP, app_config: dict) -> None:
    """
    Disable tools based on app configuration settings.
    
    Args:
        mcp: The FastMCP server instance
        app_config: App configuration data
    """
    budget_mode = app_config.get("budget_mode", False)
    allocation_mode = app_config.get("allocation_mode", False)
    
    # Budget vs Spend Plan mode tools
    if budget_mode:
        # Disable spend plan tools
        spend_plan_tools = [
            CREATE_PROJECT_WITH_SPEND_PLAN,
            GET_PROJECT_SPEND_PLAN_WITH_TOTALS, 
            ADD_PROJECT_SPEND_PLAN_ENTRIES
        ]
        disable_tools(mcp, spend_plan_tools)
        logging.info("Disabled spend plan tools (budget mode active)")
    else:
        # Disable budget tools
        budget_tools = [
            CREATE_PROJECT_WITH_BUDGET,
            CREATE_BUDGET,
            GET_OU_BUDGET,
            GET_PROJECT_BUDGET
        ]
        disable_tools(mcp, budget_tools)
        logging.info("Disabled budget tools (spend plan mode active)")
    
    # Allocation mode tools
    if not allocation_mode:
        allocation_tools = [
            ALLOCATE_FUNDS
        ]
        disable_tools(mcp, allocation_tools)
        logging.info("Disabled allocation tools (allocation mode inactive)")


def configure_config_mode(mcp: FastMCP) -> None:
    """
    Configure the server for config mode - only config tools enabled.
    
    Args:
        mcp: The FastMCP server instance
    """
    logging.info("Server in config mode - enabling config tools only")

    # Enable only the config tools; `only=True` disables every other tool.
    mcp.enable(names=set(CONFIG_MODE_TOOLS), only=True)


def setup_authentication_and_middleware(mcp: FastMCP, client, config=None, auth_manager=None) -> tuple[KionConfig, AuthManager]:
    """
    Set up authentication and middleware for the server.

    Args:
        mcp: The FastMCP server instance
        client: The shared httpx client used by both the OpenAPI tools and the
            custom tools (FastMCP 3.x no longer exposes it as ``mcp._client``).
        config: Optional existing config
        auth_manager: Optional existing auth_manager

    Returns:
        tuple: (config, auth_manager) loaded/reloaded as needed
    """
    # Reload config and auth_manager in case they were updated during config mode
    config = KionConfig.load()
    auth_manager = AuthManager(config)

    # Configure the shared httpx client. This is the same instance passed to
    # FastMCP.from_openapi, so the OpenAPI-generated tools pick up the base URL
    # and auth headers as well.
    client.base_url = config.server_base_url
    client.headers = build_standard_headers(auth_manager.get_bearer_token())

    auth_middleware = AuthenticationMiddleware(config, auth_manager, client)
    mcp.add_middleware(auth_middleware)
    mcp.add_middleware(FinancialOperationMiddleware())
    
    logging.info("Authentication and middleware configured")
    
    return config, auth_manager


def enable_all_operational_tools(mcp: FastMCP) -> None:
    """
    Enable all operational mode tools (non-config tools) and disable config tools.
    
    Args:
        mcp: The FastMCP server instance
    """
    # Enable every tool, then disable the config-only tools.
    mcp.enable(components={"tool"})
    disable_tools(mcp, CONFIG_MODE_TOOLS)
    logging.info("Enabled all operational tools")


async def configure_operational_mode(mcp: FastMCP, auth_state) -> None:
    """
    Configure the server for operational mode - API tools enabled based on app config.
    
    Args:
        mcp: The FastMCP server instance
        auth_state: Dictionary to populate with config and auth_manager references
    """
    logging.info("Server in operational mode - configuring API tools")
    enable_all_operational_tools(mcp)
    
    try:
        # Set up authentication and middleware, updating the auth_state container
        config, auth_manager = setup_authentication_and_middleware(mcp, auth_state["client"], auth_state.get("config"), auth_state.get("auth_manager"))
        
        # Update the auth_state container with the new instances
        auth_state["config"] = config
        auth_state["auth_manager"] = auth_manager
        
        # Load app config and disable tools that shouldn't be available
        app_config = await load_app_config_for_tools()
        disable_tools_based_on_config(mcp, app_config)
        
        # Apply tool description updates based on app config
        await apply_tool_description_updates(mcp, app_config)
        
    except Exception as e:
        # Error fallback - log error, leave all operational tools enabled and add maximum description options
        logging.error(f"Error configuring tools from app config: {e}")

        try:
            fallback_app_config = {
                "budget_mode": True,
                "allocation_mode": True,
                "enforce_funding": True,
                "enforce_funding_sources": True
            }
            await apply_tool_description_updates(mcp, fallback_app_config)
        except Exception as desc_error:
            logging.error(f"Failed to apply description updates in fallback mode: {desc_error}")


def _description_transform(descriptions: dict[str, str]) -> ToolTransform:
    """Build a ToolTransform overriding the given tools' descriptions.

    FastMCP 3.x serves OpenAPI tools from a provider, so descriptions must be
    overridden via a transform rather than by removing/re-adding the tool on the
    local provider (which only holds the custom tools).
    """
    return ToolTransform(
        {name: ToolTransformConfig(description=desc) for name, desc in descriptions.items()}
    )


async def update_tool_description_replace(server: FastMCP, tool_name: str, new_description: str) -> bool:
    """
    Replace a tool's description completely with new text.

    Args:
        server: The FastMCP server instance
        tool_name: Name of the tool to update
        new_description: New description to replace the existing one

    Returns:
        True if tool was updated successfully, False if tool not found
    """
    # FastMCP 3.x get_tool returns None for an unknown tool (it does not raise).
    try:
        existing_tool = await server.get_tool(tool_name)
    except NotFoundError:
        existing_tool = None
    if existing_tool is None:
        logging.warning(f"Tool '{tool_name}' not found for description replacement")
        return False

    server.add_transform(_description_transform({tool_name: new_description}))
    return True


async def update_tool_description_append(server: FastMCP, tool_name: str, append_text: str) -> bool:
    """
    Append text to a tool's existing description.

    Args:
        server: The FastMCP server instance
        tool_name: Name of the tool to update
        append_text: Text to append to the existing description

    Returns:
        True if tool was updated successfully, False if tool not found
    """
    try:
        existing_tool = await server.get_tool(tool_name)
    except NotFoundError:
        existing_tool = None
    if existing_tool is None:
        logging.warning(f"Tool '{tool_name}' not found for description append")
        return False

    current_description = existing_tool.description or ""
    new_description = current_description + "\n\n" + append_text
    server.add_transform(_description_transform({tool_name: new_description}))
    return True


async def apply_tool_description_updates(server: FastMCP, app_config: dict) -> None:
    """
    Apply tool description updates based on app configuration.

    Args:
        server: The FastMCP server instance
        app_config: App configuration data used to generate description updates
    """
    try:
        # Generate tool description appends based on app config
        tool_description_append = generate_tool_description_append(app_config)

        # Resolve each tool's current description and build a single transform
        # overriding all of them at once.
        descriptions: dict[str, str] = {}
        for tool_name, append_text in tool_description_append.items():
            try:
                existing_tool = await server.get_tool(tool_name)
            except NotFoundError:
                existing_tool = None
            if existing_tool is None:
                logging.warning(f"Tool '{tool_name}' not found for description append")
                continue
            current_description = existing_tool.description or ""
            descriptions[tool_name] = current_description + "\n\n" + append_text

        if descriptions:
            server.add_transform(_description_transform(descriptions))

        logging.debug(
            f"Applied description updates to {len(descriptions)}/{len(tool_description_append)} tools"
        )

    except Exception as e:
        logging.error(f"Error applying tool description updates: {e}")


async def configure_server_state(mcp: FastMCP, auth_state) -> None:
    """
    Configure server state and tool availability based on current configuration.
    
    Handles three modes:
    - Config mode: Only config tools enabled
    - Operational mode: API tools enabled based on app config
    - Error fallback: All tools enabled
    
    Args:
        mcp: The FastMCP server instance
        auth_state: Dictionary containing config and auth_manager references
    """
    try:
        # Check if we need configuration
        if needs_configuration():
            configure_config_mode(mcp)
        else:
            await configure_operational_mode(mcp, auth_state)
            
    except Exception as e:
        logging.error(f"Critical error in configure_server_state: {e}")
        # Ultimate fallback - enable all tools
        enable_all_operational_tools(mcp)