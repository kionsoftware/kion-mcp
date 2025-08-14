"""Configuration setup tool for Kion MCP Server."""

import logging
from fastmcp import Context
from ..interaction.elicitation import elicit_kion_url, elicit_bearer_token
from ..config.settings import KionConfig
from ..exceptions import ConfigurationError


async def setup_kion_config_impl(ctx: Context) -> str:
    """Setup Kion MCP Server configuration.
    
    Collects Kion instance URL and authentication details needed to connect.
    Must be called before any other Kion functionality is available.
    
    Args:
        ctx: FastMCP context for user interaction
        
    Returns:
        str: Configuration status message
    """
    logging.info("Starting Kion configuration setup")
    # Load existing config if it exists (may have placeholders)
    try:
        config = KionConfig.load()
    except Exception:
        config = KionConfig()
    
    # Try to elicit Kion URL
    url_result = await elicit_kion_url(ctx)
    
    if url_result is None:
        # Treat None as elicitation not supported
        url_success, kion_url = False, ""
    else:
        url_success, kion_url = url_result
    
    if url_success and kion_url.strip():
        config.server_base_url = config._process_server_url(kion_url.strip())
        logging.info(f"Successfully collected Kion URL: {kion_url}")
        
        # Try to elicit bearer token
        token_result = await elicit_bearer_token(ctx)
        
        if token_result is None:
            # Treat None as elicitation not supported
            token_success, bearer_token = False, ""
        else:
            token_success, bearer_token = token_result
        
        if token_success and bearer_token.strip():
            config.bearer_token = bearer_token.strip()
            logging.info("Successfully collected bearer token")
        # Preserve existing valid bearer token if elicitation failed/skipped
        
        # Save config file with whatever we collected
        try:
            config.save()
            
            if config.bearer_token:
                return f"""
✅ Configuration completed successfully!

Created kion_mcp_config.yaml with:
- Kion URL: {config.server_base_url}
- Authentication: Bearer token configured

All Kion API tools should now be available. If you don't see them immediately, ask the user to send another message and they should appear.
NOTE: YOU WILL NOT BE ABLE TO CALL `check_config_status` after this point, that tool is no longer active. If you don't see the complete list of tools immediately return to the user and tell them that the server should now be setup and you should have access to everything after their next message. Only if you still see the config tools then tell them to restart the client.
"""
            else:
                return f"""
⚠️ Partial configuration completed.

Created kion_mcp_config.yaml with:
- Kion URL: {config.server_base_url}

Instruct the user to get an API key from within Kion by clicking their user icon in the top right corner, then 'App API Keys', and then 'Add +'.
Then they should update the kion_mcp_config.yaml file at:
{config._config_path.resolve()}

by adding this line to the file:
bearer_token: your_bearer_token_here

Once they have completed this they will need to restart the MCP client that you are running in order to access Kion functionality.
Instruct them through this process, you are not able to update the file yourself.
"""
                
        except Exception as e:
            logging.error(f"Failed to create config file: {e}")
            return f"❌ Error creating config file: {e}"
    
    else:
        # Fallback guidance when elicitation doesn't work - point to existing placeholder file
        from pathlib import Path
        script_dir_path = (Path(__file__).parent.parent.parent.parent / 'kion_mcp_config.yaml').resolve()
        home_dir_path = (Path.home() / 'kion_mcp_config.yaml').resolve()
        return f"""
Configuration setup needed. A template config file has been created for you to edit.

The user has several options (if the first placeholder file seems hard for the user to access help them with options 2 or 3 with the note that if they're on Mac it is difficult to use textedit to make a non-rtf yaml file):
1. Edit the placeholder file at: {script_dir_path}
2. Move the placeholder file to their home directory: {home_dir_path}
3. Create a new config file in their home directory: {home_dir_path}

The file should contain (DO NOT use quotes around the values):
```yaml
server_base_url: https://their-kion-instance.com
bearer_token: their_bearer_token_here
```

The user can get the bearer token by going to their Kion instance, clicking their user icon in the top right corner, then 'App API Keys', and then 'Add +'. 

Once they have updated the placeholder values, they will need to tell you so that you can call the `check_config_status` tool to activate the Kion API tools.
You are not able to update the file yourself, you can only instruct the user through this process.
"""


async def check_config_status_impl(ctx: Context) -> str:
    """Check if the Kion configuration is now valid and ready for use.
    
    This tool checks if the configuration file has been properly set up
    and can be used to connect to Kion. If the configuration is valid,
    the server will automatically enable the Kion API tools.
    
    Args:
        ctx: FastMCP context for user interaction
        
    Returns:
        str: Configuration status message
    """
    logging.info("Checking Kion configuration status")
    try:
        config = KionConfig.load()
        
        if config.needs_configuration():
            # Config still needs server URL
            return """
❌ Configuration incomplete: Kion server URL not configured.

Please update your kion_mcp_config.yaml file with your actual Kion instance URL.
"""
        
        # Check if we have valid authentication (either bearer token or auth script)
        has_bearer = config.has_real_bearer()
        has_auth_script = config.has_auth_script()
        
        if not has_bearer and not has_auth_script:
            return """
❌ Configuration incomplete: Authentication not configured.

Please update your kion_mcp_config.yaml file with a valid bearer token.
You can get a bearer token from your Kion instance by clicking your user icon 
in the top right corner, then 'App API Keys', and then 'Add +'.
"""
        
        # Config looks complete
        logging.info("Configuration check passed - server should transition to operational mode")
        return """
✅ Configuration is valid!

Your Kion MCP Server configuration is complete and ready to use.
The server has automatically enabled all available Kion API tools.

If you don't see the tools now, please ask the user to send another message which should refresh the tool list visible to you. If the tools still don't appear after the user sends a follow-up message, instruct the user to restart whatever application you are running in (Claude Desktop, VS Code, etc.) to refresh the MCP tool definitions.
"""
            
    except ConfigurationError as e:
        return f"""
❌ Configuration error: {e}

Please check your kion_mcp_config.yaml file exists and is properly formatted.
"""
    except Exception as e:
        logging.error(f"Error checking config status: {e}")
        return f"""
❌ Error checking configuration: {e}

Please check your kion_mcp_config.yaml file.
"""