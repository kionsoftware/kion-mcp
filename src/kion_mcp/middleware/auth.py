"""Authentication middleware for Kion MCP Server."""

import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import refresh_authentication


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
                    result = await call_next(context)
                    logging.debug(f"Result after middleware retry: {result}")
                else:
                    # Refresh failed, raise the error
                    logging.error(error_msg)
                    raise Exception(error_msg)
            else:
                logging.error(f"Unexpected error: {e}")
                raise e
        return result