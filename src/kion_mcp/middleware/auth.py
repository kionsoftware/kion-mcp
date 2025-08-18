"""Authentication middleware for Kion MCP Server."""

import logging
from pathlib import Path
from fastmcp.server.middleware import Middleware, MiddlewareContext
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import refresh_authentication, get_auth_failure_message


class AuthenticationMiddleware(Middleware):
    """Middleware to handle authentication and token refresh."""
    
    def __init__(self, config: KionConfig, auth_manager: AuthManager, mcp_instance):
        self.config = config
        self.auth_manager = auth_manager
        self.mcp = mcp_instance
    
    
    async def on_request(self, context: MiddlewareContext, call_next):
        """Handle authentication for requests."""
        try:
            result = await call_next(context)
        except Exception as e:
            # Detecting that the bearer token might be expired
            if "HTTP error 401: Unauthorized" in str(e):
                logging.debug("Unauthorized error detected in middleware")
                
                # Try to refresh authentication
                ctx = context.fastmcp_context
                refresh_success, error_msg = await refresh_authentication(
                    self.config, self.auth_manager, self.mcp._client, ctx
                )
                
                if refresh_success:
                    logging.debug("Retrying request with refreshed token from middleware")
                    try:
                        result = await call_next(context)
                        logging.debug(f"Result after middleware retry: {result}")
                    except Exception as retry_error:
                        # If retry still fails with auth error, provide user guidance error message
                        if "HTTP error 401: Unauthorized" in str(retry_error) or "Authentication failed" in str(retry_error):
                            config_path = str(Path(self.config._config_path or "kion_mcp_config.yaml").resolve())
                            dxt_error = get_auth_failure_message(config_path)
                            logging.error(dxt_error)
                            raise Exception(dxt_error)
                        else:
                            raise retry_error
                else:
                    # Refresh failed, raise the error
                    logging.error(error_msg)
                    raise Exception(error_msg)
            else:
                logging.error(f"Unexpected error: {e}")
                raise e
        return result