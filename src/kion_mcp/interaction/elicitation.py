"""User elicitation utilities for Kion MCP Server."""

import logging
from typing import Tuple
from fastmcp import Context
from fastmcp.server.elicitation import (
    AcceptedElicitation, 
    DeclinedElicitation, 
    CancelledElicitation,
)
from ..constants.tools import CREATE_FUNDING_SOURCE, ALLOCATE_FUNDS


async def elicit_kion_url(ctx: Context) -> Tuple[bool, str]:
    """Elicit Kion instance URL from user."""
    try:
        result = await ctx.elicit("Enter the full url of your Kion instance e.g. https://kion.example.com", response_type=str)
        match result:
            case AcceptedElicitation(data=url):
                return True, url
            case DeclinedElicitation():
                logging.info("User declined to provide Kion URL")
                return True, ""
            case CancelledElicitation():
                logging.info("User cancelled Kion URL elicitation")
                return True, ""
    except Exception as e:
        logging.debug(f"Exception eliciting url likely due to client not supporting elicitation: {e}")
        return False, ""


async def elicit_bearer_token(ctx: Context) -> Tuple[bool, str]:
    """Elicit bearer token from user."""
    try:
        result = await ctx.elicit(
            "Enter your Kion bearer token. You can find this by clicking your user icon in the top right corner of Kion and then clicking 'App API Keys' and then click 'Add +':", 
            response_type=str
        )
        match result:
            case AcceptedElicitation(data=token):
                return True, token
            case DeclinedElicitation():
                logging.info("User declined to provide bearer token")
                return True, ""
            case CancelledElicitation():
                logging.info("User cancelled bearer token elicitation")
                return True, ""
    except Exception as e:
        logging.debug(f"Exception eliciting bearer token likely due to client not supporting elicitation: {e}")
        return False, ""


async def elicit_financial_operation_approval(ctx: Context, operation_type: str, request_data: dict) -> bool:
    """
    Elicit user approval for financial operations like funding source creation and allocation.
    Returns True if approved/elicitation not supported, False if declined.
    """
    try:
        if operation_type == CREATE_FUNDING_SOURCE:
            # Parse funding source details
            name = request_data.get("name", "Unknown")
            ou_id = request_data.get("ou_id", "Unknown")
            amount = request_data.get("amount", "Unknown")
            start_datecode = request_data.get("start_datecode", "Unknown")
            end_datecode = request_data.get("end_datecode", "Unknown")
            description = request_data.get("description", "")
            
            message = f"The AI is attempting to call Create Funding Source with:\n- Name: {name}\n- OU ID: {ou_id}\n- Amount: ${amount}\n- Start: {start_datecode}\n- End: {end_datecode}\n- Description: {description}\n\nDo you want to allow this call?"
            
        elif operation_type == ALLOCATE_FUNDS:
            # Parse allocation details
            amount = request_data.get("amount", "Unknown")
            from_ou_id = request_data.get("from_ou_id", "Unknown")
            to_ou_id = request_data.get("to_ou_id", "Unknown")
            funding_source_id = request_data.get("funding_source_id", "Unknown")
            comments = request_data.get("comments", "")
            
            message = f"The AI is attempting to call Allocate Funds with:\n- Amount: ${amount}\n- From OU ID: {from_ou_id}\n- To OU ID: {to_ou_id}\n- Funding Source ID: {funding_source_id}\n- Comments: {comments}\n\nDo you want to allow this call?"
        
        else:
            # Should not reach here for defined operations
            return True
        
        result = await ctx.elicit(message, response_type=None)
        
        match result:
            case AcceptedElicitation():
                logging.info(f"User approved {operation_type} operation")
                return True
            case DeclinedElicitation():
                logging.info(f"User declined {operation_type} operation")
                return False
            case CancelledElicitation():
                logging.info(f"User cancelled {operation_type} operation")
                return False
                
    except Exception as e:
        logging.debug(f"Exception eliciting approval for {operation_type}, likely client doesn't support elicitation: {e}")
        # If elicitation fails, proceed with operation (backward compatibility)
        return True
    
    return True