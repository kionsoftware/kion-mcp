"""Spend report tool for Kion MCP Server."""

import json
import logging
from typing import Literal, List

from httpx import AsyncClient
from fastmcp import Context
from ..parsers.spend_report import parse_spend_report
from ..config.settings import KionConfig
from ..config.auth import AuthManager
from ..utils.http_helper import make_authenticated_request


async def get_spend_report_impl(
    ctx: Context,
    start_date: str,
    end_date: str,
    dimension: Literal["none", "ou", "project", "account", "cloudProvider", "billingSource", "cloudProviderTag", "fundingSource", "label", "region", "service", "resource"] = "none",
    time_granularity_id: Literal[1, 2] = 1,
    deduct_credits: bool = True,
    deduct_refunds: bool = True,
    spend_type: Literal["attributed", "billed", "unattributed", "list"] = "attributed",
    include_timeslice_breakdown: bool = False,
    app_label_key_id_dimension: int = None,
    app_label_ids_dimension: List[int] = [],
    cloud_provider_tag_key_id_dimension: int = None,
    cloud_provider_tag_value_ids_dimension: List[int] = [],
    ou_ids: List[int] = [],
    ou_exclusive: bool = False,
    include_descendants: bool = True,
    project_ids: List[int] = [],
    project_exclusive: bool = False,
    billing_source_ids: List[int] = [],
    billing_source_exclusive: bool = False,
    funding_source_ids: List[int] = [],
    funding_source_exclusive: bool = False,
    cloud_provider_ids: List[int] = [],
    cloud_provider_exclusive: bool = False,
    account_ids: List[int] = [],
    account_exclusive: bool = False,
    service_ids: List[int] = [],
    service_exclusive: bool = False,
    include_cloud_provider_tag_ids: dict[str, List[int]] = {},
    exclude_cloud_provider_tag_ids: dict[str, List[int]] = {},
    include_app_label_ids: dict[str, List[int]] = {},
    exclude_app_label_ids: dict[str, List[int]] = {},
    mcp_http_client: AsyncClient = None,
    config: KionConfig = None,
    auth_manager: AuthManager = None
) -> str:
    """Get a spend report for the specified date range and filters.
    
    Retrieves cloud spend data with various filtering and grouping options.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date: End date in YYYY-MM-DD format (exclusive)  
        dimension: How to group the spend data (none, ou, project, account, etc.)
        time_granularity_id: Monthly (1) or daily (2) time frames
        deduct_credits: Whether to deduct credits from spend totals
        deduct_refunds: Whether to deduct refunds from spend totals
        spend_type: How spend is calculated (attributed, billed, unattributed, list)
        include_timeslice_breakdown: Include detailed time interval breakdown
        app_label_key_id_dimension: Key ID for label dimension (required when dimension='label')
        app_label_ids_dimension: Label IDs for dimensions (required when dimension='label')
        cloud_provider_tag_key_id_dimension: Tag key ID (required when dimension='cloudProviderTag')
        cloud_provider_tag_value_ids_dimension: Tag value IDs (required when dimension='cloudProviderTag')
        ou_ids: List of OU IDs to filter by
        ou_exclusive: If true, exclude specified OUs; if false, include only specified OUs
        include_descendants: Include descendant OUs in filter
        project_ids: List of project IDs to filter by
        project_exclusive: If true, exclude specified projects; if false, include only specified projects
        billing_source_ids: List of billing source IDs to filter by
        billing_source_exclusive: If true, exclude specified billing sources
        funding_source_ids: List of funding source IDs to filter by
        funding_source_exclusive: If true, exclude specified funding sources
        cloud_provider_ids: List of cloud provider IDs to filter by
        cloud_provider_exclusive: If true, exclude specified cloud providers
        account_ids: List of account IDs to filter by
        account_exclusive: If true, exclude specified accounts
        service_ids: List of service IDs to filter by
        service_exclusive: If true, exclude specified services
        include_cloud_provider_tag_ids: Include only resources with specified tags
        exclude_cloud_provider_tag_ids: Exclude resources with specified tags
        include_app_label_ids: Include only resources with specified labels
        exclude_app_label_ids: Exclude resources with specified labels
        mcp_http_client: HTTP client for API requests
        config: Kion configuration instance
        auth_manager: Authentication manager instance

    Returns:
        str: JSON string containing spend report data

    Raises:
        Exception: If required parameters are missing or API request fails
    """
    # Validate required dimension fields
    if dimension == "label":
        if app_label_key_id_dimension is None:
            raise Exception("app_label_key_id_dimension is required when dimension is 'label'. Use get_label_key_id tool to get this value.")
        if app_label_ids_dimension is None:
            raise Exception("app_label_ids_dimension is required when dimension is 'label'.")
    
    if dimension == "cloudProviderTag":
        if cloud_provider_tag_key_id_dimension is None:
            raise Exception("cloud_provider_tag_key_id_dimension is required when dimension is 'cloudProviderTag'. Use tag key tools to get this value.")
        if cloud_provider_tag_value_ids_dimension is None:
            raise Exception("cloud_provider_tag_value_ids_dimension is required when dimension is 'cloudProviderTag'.")
    
    body_dimension = dimension if dimension != "none" or time_granularity_id == 2 else "account"
    request_body = {
        "start_date": start_date,
        "end_date": end_date,
        "dimension": body_dimension,
        "time_granularity_id": time_granularity_id,
        "deduct_credits": deduct_credits,
        "deduct_refunds": deduct_refunds,
        "spend_type": spend_type,
        "ou_ids": ou_ids,
        "ou_exclusive": ou_exclusive,
        "include_descendants": include_descendants,
        "project_ids": project_ids,
        "project_exclusive": project_exclusive,
        "billing_source_ids": billing_source_ids,
        "billing_source_exclusive": billing_source_exclusive,
        "funding_source_ids": funding_source_ids,
        "funding_source_exclusive": funding_source_exclusive,
        "cloud_provider_ids": cloud_provider_ids,
        "cloud_provider_exclusive": cloud_provider_exclusive,
        "account_ids": account_ids,
        "account_exclusive": account_exclusive,
        "service_ids": service_ids,
        "service_exclusive": service_exclusive,
        "include_cloud_provider_tag_ids": include_cloud_provider_tag_ids,
        "exclude_cloud_provider_tag_ids": exclude_cloud_provider_tag_ids,
        "include_app_label_ids": include_app_label_ids,
        "exclude_app_label_ids": exclude_app_label_ids,
    }
    
    # Add dimension-specific fields only when needed
    if dimension == "label":
        request_body["app_label_key_id_dimension"] = app_label_key_id_dimension
        request_body["app_label_ids_dimension"] = app_label_ids_dimension
    elif dimension == "cloudProviderTag":
        request_body["cloud_provider_tag_key_id_dimension"] = cloud_provider_tag_key_id_dimension
        request_body["cloud_provider_tag_value_ids_dimension"] = cloud_provider_tag_value_ids_dimension

    logging.debug(f"Request body for spend report: {request_body}")

    response = await make_authenticated_request(
        mcp_http_client, "POST", "/v1/spend-report", config, auth_manager, ctx, 
        json=request_body, timeout=20.0
    )
    
    logging.debug("Successfully retrieved spend report")
    raw_data = json.loads(response.text)
    if raw_data is None or "data" not in raw_data or raw_data["data"] is None:
        return json.dumps({"message": "No spend data returned, either no spend exists for query or the user may not have permission to generate the spend report", "api_response": raw_data}, indent=2)
    parsed_data = parse_spend_report(raw_data, spend_type, deduct_credits, deduct_refunds, include_timeslice_breakdown, dimension)
    logging.debug("Parsed spend report data successfully")
    return json.dumps(parsed_data, indent=2)