"""Custom tool registrations for Kion MCP Server."""

from typing import Annotated, Literal, List
from pydantic import Field
from fastmcp import FastMCP, Context

from .config_tool import setup_kion_config_impl, check_config_status_impl
from .spend_report import get_spend_report_impl
from .label_tools import get_label_key_id_impl
from .entity_tools import get_entity_by_id_impl
from .cloud_access_role_tools import get_cloud_access_roles_on_entity_impl, get_cloud_access_role_details_impl
from .user_info import get_user_info_impl
from ..server_management.tool_manager import configure_server_state


def register_custom_tools(mcp: FastMCP, auth_state):
    """Register all custom MCP tools with the server."""
    
    # NOTE: When adding a new tool ensure that you're also adding a const for it in src/kion_mcp/constants/tools.py
    @mcp.tool
    async def setup_kion_config(ctx: Context) -> str:
        """
        REQUIRED SETUP: This Kion MCP Server is missing required configuration.
        
        Call this tool to begin setup. It will try to collect your Kion instance URL and authentication details.
        
        After calling this tool:
        - If it returns "Configuration completed successfully!" and says tools should now be available, then all Kion API tools are ready. If you don't see them, ask the user to send another message.
        - If it requires manual configuration, follow the instructions provided, then call check_config_status to activate the API tools.

        Once setup is complete, you can use this server to help the user report on their cloud spend, cloud compliance, Kion org chart and budgeting management, and other Kion features.
        """
        result = await setup_kion_config_impl(ctx)
        # After setup, trigger tool availability update
        await configure_server_state(mcp, auth_state)
        return result
    
    @mcp.tool
    async def check_config_status(ctx: Context) -> str:
        """
        Call this tool AFTER manually updating the config file to activate API tools.
        ONLY call this tool if the setup_kion_config tool required manual config and the user says they've completed those steps. DO NOT CALL IT ON SUCCESSFUL CONFIGURATION.
        
        This tool verifies the configuration is valid and activates all Kion API tools.
        Only needed if setup_kion_config required manual configuration steps.
        
        After calling this tool, all Kion API tools should be available. If you don't see them, ask the user to send another message.
        """
        result = await check_config_status_impl(ctx)
        # After check, trigger tool availability update
        await configure_server_state(mcp, auth_state)
        return result
    
    @mcp.tool
    async def get_spend_report(
        ctx: Context,
        start_date: Annotated[str, Field(description="Start date for the report in YYYY-MM-DD format. Start date is INCLUSIVE.", pattern=r"^\d{4}-\d{2}-\d{2}$")],
        end_date: Annotated[str, Field(description="End date for the report in YYYY-MM-DD format. End date is EXCLUSIVE.", pattern=r"^\d{4}-\d{2}-\d{2}$")],
        dimension: Annotated[str, Field(description="What groupings of spend are returned, like spend by Kion project or spend by cloud provider. If using this filter valid dimensions include: none, ou, project, account, cloudProvider, billingSource, cloudProviderTag, fundingSource, label, region, service, resource"), Literal["none", "ou", "project", "account", "cloudProvider", "billingSource", "cloudProviderTag", "fundingSource", "label", "region", "service", "resource"]] = "none",
        time_granularity_id: Annotated[int, Field(description="Whether the report is split into monthly (1) or daily (2) time frames. `1`and `2` are the only valid options."), Literal[1, 2]] = 1,
        deduct_credits: Annotated[bool, Field(description="Whether to to deduct credits from spend or split them out into a separate field")] = True,
        deduct_refunds: Annotated[bool, Field(description="Whether to to deduct refunds from spend or split them out into a separate field")] = True,
        spend_type: Annotated[str, Field(description="How spend is calculated, amortized and attributed which shows spend spread across the time-period it occurred attributed to the correct accounts (`attributed`), `billed` what's invoiced from the provider (default value), amortized spend spread across the time it occurs but not attributed and shown at the billing source level (`unattributed`), or `list` the public list price"), Literal["attributed", "billed", "unattributed", "list"]] = "billed",
        include_timeslice_breakdown: Annotated[bool, Field(description="Whether to include detailed breakdown by time intervals or just totals")] = False,
        app_label_key_id_dimension: Annotated[int, Field(description="REQUIRED when dimension is 'label', type int. The key ID for the label dimension. Use get_label_key_id tool to get this value.")] = None,
        app_label_ids_dimension: Annotated[List[int], Field(description="REQUIRED when dimension is 'label', type int. List of label IDs to show as dimensions. Empty list shows shows all values as dimensions, specific IDs show only those values.")] = [],
        cloud_provider_tag_key_id_dimension: Annotated[int, Field(description="REQUIRED when dimension is 'cloudProviderTag'. The tag key ID for the tag dimension. Use tag key tools to get this value.")] = None,
        cloud_provider_tag_value_ids_dimension: Annotated[List[int], Field(description="REQUIRED when dimension is 'cloudProviderTag'. List of tag value IDs to show as dimensions. Empty list shows all values as dimensions and a dimension for everything without that key tag, specific IDs show only those values, include 0 with other IDs to also show resources without this tag key.")] = [],
        ou_ids: Annotated[List[int], Field(description="List of OU (kion organizational unit) IDs to filter by")] = [],
        ou_exclusive: Annotated[bool, Field(description="If true, exclude the specified OU IDs; if false, include only the specified OU IDs")] = False,
        include_descendants: Annotated[bool, Field(description="Whether to include descendant OUs in the filter (only applies to OU filters)")] = True,
        project_ids: Annotated[List[int], Field(description="List of project (mostly account specific in kion) IDs to filter by")] = [],
        project_exclusive: Annotated[bool, Field(description="If true, exclude the specified project IDs; if false, include only the specified project IDs")] = False,
        billing_source_ids: Annotated[List[int], Field(description="List of billing source IDs to filter by")] = [],
        billing_source_exclusive: Annotated[bool, Field(description="If true, exclude the specified billing source IDs; if false, include only the specified billing source IDs")] = False,
        funding_source_ids: Annotated[List[int], Field(description="List of funding source IDs to filter by")] = [],
        funding_source_exclusive: Annotated[bool, Field(description="If true, exclude the specified funding source IDs; if false, include only the specified funding source IDs")] = False,
        cloud_provider_ids: Annotated[List[int], Field(description="List of cloud provider IDs to filter by)")] = [],
        cloud_provider_exclusive: Annotated[bool, Field(description="If true, exclude the specified cloud provider IDs; if false, include only the specified cloud provider IDs")] = False,
        account_ids: Annotated[List[int], Field(description="List of account IDs to filter by")] = [],
        account_exclusive: Annotated[bool, Field(description="If true, exclude the specified account IDs; if false, include only the specified account IDs")] = False,
        service_ids: Annotated[List[int], Field(description="List of service IDs to filter by. You can get these IDs using the CSP Service get tool.")] = [],
        service_exclusive: Annotated[bool, Field(description="If true, exclude the specified service IDs; if false, include only the specified service IDs")] = False,
        include_cloud_provider_tag_ids: Annotated[dict[str, List[int]], Field(description="Filter including only the passed cloud provider tags. The map key is the str of the key ID, the list of ints are that key's value IDs (passing an empty list applies filter to all values of key). Use tag key and value tools to get these IDs.")] = {},
        exclude_cloud_provider_tag_ids: Annotated[dict[str, List[int]], Field(description="Filter to exclude the passed cloud provider tags. The map key is the str of the key ID, the list of ints are that key's value IDs (passing an empty list applies filter to all values of key). Use tag key and value tools to get these IDs.")] = {},
        include_app_label_ids: Annotated[dict[str, List[int]], Field(description="Filter including only the passed Kion app labels. The map key is the str of the key ID, the list of ints are that key's value IDs (passing an empty list applies filter to all values of key). Use the label key tool to get the key ID.")] = {},
        exclude_app_label_ids: Annotated[dict[str, List[int]], Field(description="Filter to exclude the passed Kion app labels. The map key is the str of the key ID, the list of ints are that key's value IDs (passing an empty list applies filter to all values of key). Use the label key tool to get the key ID.")] = {}
    ) -> str:
        """
        Get a spend report for the specified date range and filters. This can be dimensioned on many different things like Kion org structures, cloud provider info, and more.
        Note that OUs are the primary organizational method in Kion and will likely be your primary filter unless asked for a specific other filter case.
        NOTE: If more than 20 dimensions are returned, only the top 19 dimensions by spend will be shown individually, with all remaining dimensions aggregated into an "other" category (e.g., "other services", "other accounts", etc.).
        NOTE: This tool is in beta. If there is a non-authentication error with the request or a server error handling the response (or the returns are empty unexpectedly like if 0 spend is unexpected) that means the MCP server is outdated. If you get either of these errors direct the user to update their MCP server, they most likely installed it with either pypi and just need to use pip to update their 'kion-mcp-server' package or via dxt and need to redownload and install the latest dxt. After they complete the update they will need to restart the MCP server most likely by restarting the client you are running in. Direct and help the user through this process.
        Always try to use this tool to get the exact number you are passing to the user, only do analysis to derive other numbers if you have access to analysis or code execution tools which you can then use to ensure exact results.
        When filtering on something you'll almost certainly NEED an ID for it, look at other tools you can call to get any IDs BEFORE calling this tool. CAREFULLY review your filter options and ensure you're using the correct one with the correct IDs.
        IMPORTANT!: UNLESS you are in daily mode (time_granularity_id=2) you MUST ensure the start date is the first of a month and the end date is the first of the excluded end month, otherwise you will get an error. In monthly or by default dates MUST have 01 as their day, e.g., 2023-01-01 to 2023-02-01. DO NOT pass a day other than 01 like 2025-07-31 UNLESS you are in daily mode.
        """
        return await get_spend_report_impl(
            ctx=ctx,
            start_date=start_date,
            end_date=end_date,
            dimension=dimension,
            time_granularity_id=time_granularity_id,
            deduct_credits=deduct_credits,
            deduct_refunds=deduct_refunds,
            spend_type=spend_type,
            include_timeslice_breakdown=include_timeslice_breakdown,
            app_label_key_id_dimension=app_label_key_id_dimension,
            app_label_ids_dimension=app_label_ids_dimension,
            cloud_provider_tag_key_id_dimension=cloud_provider_tag_key_id_dimension,
            cloud_provider_tag_value_ids_dimension=cloud_provider_tag_value_ids_dimension,
            ou_ids=ou_ids,
            ou_exclusive=ou_exclusive,
            include_descendants=include_descendants,
            project_ids=project_ids,
            project_exclusive=project_exclusive,
            billing_source_ids=billing_source_ids,
            billing_source_exclusive=billing_source_exclusive,
            funding_source_ids=funding_source_ids,
            funding_source_exclusive=funding_source_exclusive,
            cloud_provider_ids=cloud_provider_ids,
            cloud_provider_exclusive=cloud_provider_exclusive,
            account_ids=account_ids,
            account_exclusive=account_exclusive,
            service_ids=service_ids,
            service_exclusive=service_exclusive,
            include_cloud_provider_tag_ids=include_cloud_provider_tag_ids,
            exclude_cloud_provider_tag_ids=exclude_cloud_provider_tag_ids,
            include_app_label_ids=include_app_label_ids,
            exclude_app_label_ids=exclude_app_label_ids,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"]
        )

    @mcp.tool
    async def get_label_key_id(
        ctx: Context,
        label_id: Annotated[int, Field(description="The label ID to get the key ID for")]
    ) -> str:
        """
        Get a label's key ID by label ID. This is used to get the key ID needed for tag filtering operations.
        """
        return await get_label_key_id_impl(
            ctx=ctx,
            label_id=label_id,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"]
        )

    @mcp.tool
    async def get_entity_by_id(
        ctx: Context,
        entity_type: Annotated[Literal["account", "ou", "project"], Field(description="Type of entity to retrieve. Must be one of 'account', 'ou', or 'project'")],
        entity_id: Annotated[int, Field(description="The ID of the entity to retrieve")]
    ) -> str:
        """Get entity details by ID and type.
        
        This tool retrieves details for OUs, projects, or accounts
        by their ID. It replaces the individual GET operations for each entity type.
        """
        return await get_entity_by_id_impl(
            ctx=ctx,
            entity_type=entity_type,
            entity_id=entity_id,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"]
        )

    @mcp.tool
    async def get_cloud_access_roles_on_entity(
        ctx: Context,
        entity_type: Annotated[Literal["project", "ou"], Field(description="Type of entity to get cloud access roles for. Must be 'project' or 'ou'")],
        entity_id: Annotated[int, Field(description="The ID of the entity to get cloud access roles for")]
    ) -> str:
        """Get cloud access roles on an entity by ID and entity type (project or ou). This will include both local and inherited CARs.
        NOTE: CARs are how Kion manages user permissions in the cloud. Get this to then get IAMs, SCPs, and other policies.
        """
        return await get_cloud_access_roles_on_entity_impl(
            ctx=ctx,
            entity_type=entity_type,
            entity_id=entity_id,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"]
        )

    @mcp.tool
    async def get_cloud_access_role_details(
        ctx: Context,
        role_type: Annotated[Literal["project", "ou"], Field(description="Type of cloud access role. Must be 'project' or 'ou'")],
        role_id: Annotated[int, Field(description="The ID of the cloud access role to get details for")]
    ) -> str:
        """Get detailed cloud access role information by ID (the specific CAR id, you'll need to know this before calling this tool) and role type (project or ou). This includes embedded IAM policies, Azure roles, GCP roles, accounts, and user/group mappings.
        """
        return await get_cloud_access_role_details_impl(
            ctx=ctx,
            role_type=role_type,
            role_id=role_id,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"]
        )

    @mcp.tool
    async def get_user_info(
        ctx: Context,
        user_type: Annotated[Literal["me", "user", "user_group"], Field(description="Type of user info to retrieve. 'me' for current user, 'user' for specific user, 'user_group' for user group")],
        user_id: Annotated[int, Field(description="The ID of the user or user group (required for 'user' and 'user_group' types)")] = 0
    ) -> str:
        """Get user information by type and ID. Use 'me' for current user ID, 'user' for specific user details, or 'user_group' for user group information. user and user group will return what users are in a group or what groups a user is in.
        """
        return await get_user_info_impl(
            ctx=ctx,
            mcp_http_client=mcp._client,
            config=auth_state["config"],
            auth_manager=auth_state["auth_manager"],
            user_type=user_type,
            user_id=user_id
        )