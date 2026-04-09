"""Configuration setup tool for Kion MCP Server."""

import logging
from fastmcp import Context
from ..interaction.elicitation import (
    elicit_kion_url,
    elicit_bearer_token,
    elicit_auth_method,
    elicit_oauth_client_id,
)
from ..config.settings import KionConfig
from ..config.oauth import OAuthManager
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
    try:
        config = KionConfig.load()
    except Exception:
        config = KionConfig()

    # Try to elicit Kion URL
    url_result = await elicit_kion_url(ctx)

    if url_result is None:
        url_success, kion_url = False, ""
    else:
        url_success, kion_url = url_result

    if url_success and kion_url.strip():
        config.server_base_url = config._process_server_url(kion_url.strip())
        logging.info(f"Successfully collected Kion URL: {kion_url}")

        # Ask for auth method
        method_success, auth_method = await elicit_auth_method(ctx)

        if method_success and auth_method == "oauth":
            # OAuth flow
            client_id_success, client_id = await elicit_oauth_client_id(ctx)
            if client_id_success and client_id.strip():
                config.oauth_client_id = client_id.strip()
                config.bearer_token = None
                config.save()

                # Run device flow to validate
                oauth_mgr = OAuthManager(config)
                success, token_or_msg = await oauth_mgr.run_device_flow(ctx)

                if success:
                    return f"""
✅ Configuration completed successfully!

Created kion_mcp_config.yaml with:
- Kion URL: {config.server_base_url}
- Authentication: OAuth Device Flow (client_id: {config.oauth_client_id})

OAuth token cached. All Kion API tools should now be available.
NOTE: YOU WILL NOT BE ABLE TO CALL `check_config_status` after this point, that tool is no longer active. If you don't see the complete list of tools immediately return to the user and tell them that the server should now be setup and you should have access to everything after their next message. Only if you still see the config tools then tell them to restart the client.
"""
                else:
                    return f"""
⚠️ Partial configuration completed.

Created kion_mcp_config.yaml with:
- Kion URL: {config.server_base_url}
- OAuth Client ID: {config.oauth_client_id}

OAuth device flow failed: {token_or_msg}
The configuration has been saved. On next restart, the server will attempt OAuth authentication again.
"""
            else:
                return "❌ OAuth Client ID is required for OAuth authentication."

        elif method_success and auth_method == "auth_script":
            return f"""
⚠️ Partial configuration completed.

Created kion_mcp_config.yaml with:
- Kion URL: {config.server_base_url}

To complete setup, add the following to your kion_mcp_config.yaml:
auth_script_path: /path/to/your/auth/script.sh

The script should output a valid bearer token to stdout.
"""

        else:
            # Bearer token flow (default / original behavior)
            token_result = await elicit_bearer_token(ctx)

            if token_result is None:
                token_success, bearer_token = False, ""
            else:
                token_success, bearer_token = token_result

            if token_success and bearer_token.strip():
                config.bearer_token = bearer_token.strip()
                logging.info("Successfully collected bearer token")

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

Alternatively, for OAuth authentication:
```yaml
server_base_url: https://their-kion-instance.com
oauth_client_id: their_oauth_client_id_here
```

The user can get a bearer token by going to their Kion instance, clicking their user icon in the top right corner, then 'App API Keys', and then 'Add +'.

Once they have updated the placeholder values, they will need to tell you so that you can call the `check_config_status` tool to activate the Kion API tools.
You are not able to update the file yourself, you can only instruct the user through this process.
"""


async def check_config_status_impl(ctx: Context) -> str:
    """Check if the Kion configuration is now valid and ready for use."""
    logging.info("Checking Kion configuration status")
    try:
        config = KionConfig.load()

        if config.needs_configuration():
            return """
❌ Configuration incomplete: Kion server URL not configured.

Please update your kion_mcp_config.yaml file with your actual Kion instance URL.
"""

        has_bearer = config.has_real_bearer()
        has_auth_script = config.has_auth_script()
        has_oauth = config.is_oauth_mode()

        if not has_bearer and not has_auth_script and not has_oauth:
            return """
❌ Configuration incomplete: Authentication not configured.

Please update your kion_mcp_config.yaml file with one of:
- bearer_token: your_api_key_here
- oauth_client_id: your_client_id_here
- auth_script_path: /path/to/script.sh
"""

        auth_method = "OAuth" if has_oauth else ("Auth Script" if has_auth_script else "Bearer Token")
        logging.info("Configuration check passed - server should transition to operational mode")
        return f"""
✅ Configuration is valid!

Your Kion MCP Server configuration is complete and ready to use.
Authentication method: {auth_method}
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
