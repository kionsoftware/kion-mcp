"""Financial operation middleware for Kion MCP Server."""

import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from ..interaction.elicitation import elicit_financial_operation_approval
from ..exceptions import UserDeniedOperationError
from ..constants.tools import CREATE_FUNDING_SOURCE, ALLOCATE_FUNDS


class FinancialOperationMiddleware(Middleware):
    """Middleware to handle financial operation approvals."""

    async def on_call_tool(self, context, call_next):
        """Check if this is a financial operation that requires approval."""
        tool_name = context.message.name
        tool_arguments = context.message.arguments or {}
        
        # Check for financial operations that require approval
        if tool_name in [CREATE_FUNDING_SOURCE, ALLOCATE_FUNDS]:
            ctx = context.fastmcp_context
            if ctx:
                try:
                    approved = await elicit_financial_operation_approval(ctx, tool_name, tool_arguments)
                    
                    if not approved:
                        # User declined - raise exception to prevent tool execution
                        raise UserDeniedOperationError("User denied the tool call. Stop what you're doing immediately and ask for clarification.")
                except UserDeniedOperationError:
                    # Re-raise user denial to block the operation
                    raise
                except Exception as e:
                    logging.debug(f"Error in financial operation ({tool_name}) approval elicitation: {e}")
                    # Continue with operation if elicitation fails
        
        # Continue with the operation
        return await call_next(context)