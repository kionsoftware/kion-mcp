"""Account tools for Kion MCP Server."""

import logging
import json
from typing import List
from fastmcp import Context
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request

# Map account_type_id to human-readable cloud provider names
ACCOUNT_TYPE_NAMES = {
    1: "AWS Standard",
    2: "AWS GovCloud",
    3: "Azure CSP Standard",
    4: "AWS C2S",
    5: "AWS SC2S",
    6: "Azure EA",
    7: "Azure Government EA",
    8: "Azure CSP Resource Group",
    9: "Azure EA Resource Group",
    10: "Azure Government EA Resource Group",
    11: "Azure Government CSP",
    12: "Azure Government CSP Resource Group",
    13: "Azure Secret EA",
    14: "Azure Secret EA Resource Group",
    15: "Google Cloud Standard",
    16: "Azure MCA",
    17: "Azure MCA Resource Group",
    18: "Azure Government MCA",
    19: "Azure Government MCA Resource Group",
    20: "Azure CSP Top Secret",
    21: "Azure CSP Top Secret Resource Group",
    22: "Azure EA Top Secret",
    23: "Azure EA Top Secret Resource Group",
    24: "Azure MCA Top Secret",
    25: "Azure MCA Top Secret Resource Group",
    26: "OCI Commercial",
    27: "OCI Government",
    28: "OCI Federal",
    29: "Custom Account",
}


def _format_account(data: dict) -> dict:
    """Format a raw API account object into a clean, MCP-friendly representation."""
    account_type_id = data.get("account_type_id")
    result = {
        "id": data.get("id"),
        "account_number": data.get("account_number"),
        "account_name": data.get("account_name"),
        "account_type_id": account_type_id,
        "account_type": ACCOUNT_TYPE_NAMES.get(account_type_id, f"Unknown ({account_type_id})"),
        "project_id": data.get("project_id"),
        "payer_id": data.get("payer_id"),
        "created_at": data.get("created_at"),
        "start_datecode": data.get("start_datecode"),
        "account_email": data.get("account_email"),
    }

    # Only include optional fields when they have meaningful values
    if data.get("account_alias"):
        result["account_alias"] = data["account_alias"]
    if data.get("linked_account_number"):
        result["linked_account_number"] = data["linked_account_number"]

    return result


async def get_accounts_impl(
    ctx: Context,
    mcp_http_client,
    config: KionConfig,
    auth_manager: AuthManager,
    account_number: str | None = None,
    name: str | None = None,
    alias: str | None = None,
    account_type_ids: List[int] | None = None,
) -> str:
    """Get accounts from Kion, either by looking up a specific cloud account number or listing/filtering accounts.

    Args:
        ctx: FastMCP context
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance
        account_number: Optional cloud provider account identifier for direct lookup
        name: Optional name pattern to filter accounts by
        alias: Optional exact account alias to filter by
        account_type_ids: Optional list of account type IDs to filter by (OR logic)

    Returns:
        str: JSON string with account details
    """
    has_filters = any([name, alias, account_type_ids])

    # account_number alone -> direct lookup endpoint
    if account_number and not has_filters:
        logging.debug(f"Looking up account by account number: {account_number}")
        endpoint = f"/v3/account/by-account-number/{account_number}"
        response = await make_authenticated_request(
            mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
        )
        data = response.json().get("data", {})
        result = _format_account(data)
        logging.debug(f"Found account {account_number} (Kion ID: {result['id']})")
        return json.dumps(result, indent=2)

    # List endpoint with optional server-side filters
    logging.debug("Listing accounts")
    query_parts = []
    if name:
        query_parts.append(f"name={name}")
    if alias:
        query_parts.append(f"alias={alias}")
    if account_type_ids:
        for type_id in account_type_ids:
            query_parts.append(f"account_type={type_id}")

    endpoint = "/v3/account"
    if query_parts:
        endpoint = f"{endpoint}?{'&'.join(query_parts)}"

    response = await make_authenticated_request(
        mcp_http_client, "GET", endpoint, config, auth_manager, ctx, timeout=20.0
    )
    data = response.json().get("data", [])

    # Client-side account_number filter when combined with other filters
    if account_number:
        data = [a for a in data if a.get("account_number") == account_number]

    results = [_format_account(account) for account in data]
    logging.debug(f"Found {len(results)} accounts")
    return json.dumps(results, indent=2)
