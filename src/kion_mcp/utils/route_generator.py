"""Route generation utilities for Kion MCP Server."""

from typing import Dict, Any


def generate_tool_description_append(app_config: Dict[str, Any]) -> Dict[str, str]:
    """Generate tool description appends based on app config."""
    descriptions = {
        "get_compliance_findings": "There are 5 compliance levels: 1 informational, 2 low, 3 medium, 4 high, and 5 critical. When calling this tool ALWAYS specify a count and page parameter, responses can be very large so using pagination is critical. It's also highly recommended to control the response with filters as much as possible. The `finding_type ` parameter MUST be either `active` or `archived`",
        "get_permission_scheme": "NOTE: This tool is only useful for getting a permission scheme ID for endpoints that need it",
        "create_project_with_budget": "NOTE: it is Kion best practice to have a one project per account relationship. Projects need to have an owner, have an owner user id or user group id ready before calling this tool.",
        "create_project_with_spend_plan": "NOTE: it is Kion best practice to have a one project per account relationship. Projects need to have an owner, have an owner user id or user group id ready before calling this tool.",
        "create_funding_source": "Funding sources can only be created on top level ous. DO NOT!!! create a funding source without explicit user permission on the details. ALWAYS!! ask the user for permission before using this tool.",
        "allocate_funds": "You can use this tool to allocate funding source funds from a parent ou to a child ou. THIS IS AN IMPORTANT FINANCIAL OPERATION! ALWAYS ask the user for explicit permission before using this tool.",
        "get_cloud_providers": "Call this before using cloud provider IDs in the spend report tool.",
        "create_ou": "OUs need to have an owner, have an owner user id or user group id ready before calling this tool."
    }
    
    # Add conditional descriptions based on config flags
    enforce_funding = app_config.get("enforce_funding", False)
    enforce_funding_sources = app_config.get("enforce_funding_sources", False)
    allocation_mode = app_config.get("allocation_mode", False)
    budget_mode = app_config.get("budget_mode", False)
    
    if enforce_funding:
        funding_msg = "\n\nFUNDING REQUIREMENT: Budget/spend plan required for project creation."
        descriptions["create_project_with_budget"] = funding_msg
        descriptions["create_project_with_spend_plan"] = funding_msg
    
    if enforce_funding_sources:
        base_funding_msg = "\n\nFUNDING REQUIREMENT: Must link funding sources with sufficient funds for the entire time period. Check GET /v3/ou/{id}/funding-source for availability."
        
        if allocation_mode:
            allocation_msg = " The system is in allocation mode meaning that the parent ou will need to have appropriate funds allocated to it. Check 'available' and 'allocated_in' fields to check the ou's allocation. If insufficient, ask the user if you can allocate funds from the top level ou's funding sources or if you can create a new funding source."
            funding_source_msg = base_funding_msg + allocation_msg
        else:
            funding_source_msg = base_funding_msg
        
        if budget_mode:
            descriptions["create_budget"] = funding_source_msg
        else:
            # For spend plan mode - add to project creation with spend plan
            descriptions["create_project_with_spend_plan"] = funding_source_msg
    
    return descriptions


