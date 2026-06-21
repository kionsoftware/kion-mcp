"""Authentication management for Kion MCP Server."""

import os
import subprocess
import logging
from pathlib import Path
from .settings import KionConfig
from ..exceptions import AuthenticationError
from ..interaction.elicitation import elicit_bearer_token


class AuthManager:
    """Manages authentication for Kion API."""

    def __init__(self, config: KionConfig):
        self.config = config
        self._oauth_manager = None

        # Lazily create OAuthManager if oauth_client_id is configured
        if config.is_oauth_mode():
            from .oauth import OAuthManager
            self._oauth_manager = OAuthManager(config)

    def get_bearer_token(self, reload_config: bool = False) -> str:
        """Get bearer token from config, OAuth cache, or auth script.

        Priority: bearer_token > cached OAuth token > auth script.

        Note: For OAuth device flow (which is async), callers should use
        the 401 retry mechanism which calls refresh_bearer_token_with_elicitation().
        This sync method only checks synchronous sources.

        Args:
            reload_config: If True, reload config from file before getting token
        """
        logging.info("Getting bearer token")

        # Reload config from file if requested
        if reload_config:
            logging.info("Reloading config from file")
            try:
                self.config.reload()
            except Exception as e:
                logging.warning(f"Failed to reload config: {e}")

        # Priority 1: Static bearer token
        if self.config.bearer_token and not self.config._is_placeholder_value('bearer_token', self.config.bearer_token):
            logging.info("Using bearer token from config")
            return self.config.bearer_token

        # Priority 2: Cached OAuth token (sync check only)
        if self._oauth_manager:
            cache = self._oauth_manager._load_token_cache()
            if cache and cache.get("access_token"):
                expires_at = cache.get("access_token_expires_at", 0)
                if not self._oauth_manager._is_token_expired(expires_at):
                    logging.info("Using cached OAuth access token")
                    return cache["access_token"]
            # OAuth is configured but no valid cached token —
            # return what we have and let the 401 retry handle async refresh
            if cache and cache.get("access_token"):
                logging.info("Using expired OAuth token (will refresh on 401)")
                return cache["access_token"]

        # Priority 3: Auth script
        if self.config.auth_script_path:
            return self._get_token_from_script()

        # Priority 4: Fall back to bearer_token even if it looks like a placeholder
        if self.config.bearer_token:
            logging.info("Using bearer token from config file")
            return self.config.bearer_token

        raise AuthenticationError("No authentication method configured (bearer_token, oauth_client_id, or auth_script_path)")

    def _get_token_from_script(self) -> str:
        """Get bearer token from auth script."""
        auth_script_path = self.config.auth_script_path

        try:
            # Support both absolute and relative paths
            if not os.path.isabs(auth_script_path):
                # Make relative to the root of the project
                auth_script_path = (Path(__file__).parent.parent.parent.parent / auth_script_path).resolve()

            logging.info(f"Executing auth script at: {auth_script_path}")
            result = subprocess.run([auth_script_path], capture_output=True, text=True, check=True)
            bearer_token = result.stdout.strip()
            logging.info(f"Successfully retrieved bearer token from auth script")
            return bearer_token

        except subprocess.CalledProcessError as e:
            raise AuthenticationError(f"Failed to get bearer token from auth script: {e}")
        except Exception as e:
            raise AuthenticationError(f"Error executing auth script: {e}")

    async def refresh_bearer_token_with_elicitation(self, ctx=None):
        """Try to refresh bearer token via OAuth, elicitation, or script.

        Priority for refresh:
        1. OAuth refresh token (if in OAuth mode)
        2. OAuth device flow re-auth (if in OAuth mode)
        3. Auth script re-execution (if in script mode)
        4. Elicitation for new bearer token (interactive)
        """
        # OAuth mode: try refresh, then device flow
        if self._oauth_manager:
            # Try refresh token first
            success, token_or_msg = await self._oauth_manager.refresh_access_token()
            if success:
                return True, token_or_msg

            # Try device flow re-auth
            success, token_or_msg = await self._oauth_manager.run_device_flow(ctx)
            if success:
                return True, token_or_msg

            return False, f"OAuth authentication failed: {token_or_msg}"

        # Script mode: re-execute script
        if self.config.is_script_auth_mode():
            token = self.get_bearer_token()
            return bool(token), token

        # Interactive mode: elicit new token
        if ctx is None:
            return False, "No context available for token elicitation"

        logging.info("Attempting to elicit new bearer token")
        success, new_token = await elicit_bearer_token(ctx)
        new_token = new_token.strip()

        if success and new_token:
            try:
                self.config.bearer_token = new_token
                self.config.save()
                logging.info("Successfully updated config with new bearer token")
                return True, new_token
            except Exception as e:
                logging.error(f"Failed to update config with new token: {e}")
                return False, f"Failed to save new token: {e}"

        return False, "Token elicitation failed or was cancelled"