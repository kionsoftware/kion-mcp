"""Route definitions for Kion MCP Server."""

from fastmcp.server.openapi import RouteMap, MCPType


# NOTE: When adding a new tool ensure that you're also adding a readable name and const for it in src/kion_mcp/constants/tools.py

# Static routes - all possible routes (tool availability managed via enable/disable)
KION_ROUTES = [
    # Base routes
    RouteMap(methods=["GET"], pattern=r"^/v3/account$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET", "POST"], pattern=r"^/v3/ou$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/ou/[^/]+/funding-source$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/project$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/permission-scheme/type/[^/]+$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/v3/funding-source$", mcp_type=MCPType.TOOL),
    
    # Budget mode routes
    RouteMap(methods=["POST"], pattern=r"^/v3/project/with-budget$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/v3/budget$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["PUT"], pattern=r"^/v3/budget/[^/]+$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/ou/[^/]+/budget$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/project/[^/]+/budget$", mcp_type=MCPType.TOOL),
    
    # Spend plan mode routes  
    RouteMap(methods=["POST"], pattern=r"^/v3/project/with-spend-plan$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/project/[^/]+/spend-plan-with-totals$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/v4/project/[^/]+/spend-plan$", mcp_type=MCPType.TOOL),
    
    # Allocation mode routes
    RouteMap(methods=["POST"], pattern=r"^/v3/transaction/allocate$", mcp_type=MCPType.TOOL),
    
    # Compliance endpoints
    RouteMap(methods=["GET"], pattern=r"^/v4/compliance/finding$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/compliance/ou$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/compliance/check/[^/]+$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v4/compliance/finding/suppressed$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v4/compliance/standard$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v4/compliance/check$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/compliance/standard/[^/]+$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v4/compliance/program/[^/]+$", mcp_type=MCPType.TOOL),
    
    # Cloud provider endpoints
    RouteMap(methods=["GET"], pattern=r"^/v3/cloud-provider$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/cloud-provider/service$", mcp_type=MCPType.TOOL),
    
    # Tags and labels
    RouteMap(methods=["GET"], tags={"tags"}, mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/label$", mcp_type=MCPType.TOOL),
    
    # User and user group endpoints
    RouteMap(methods=["GET"], pattern=r"^/v3/user$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/user-group$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"], pattern=r"^/v3/user/[^/]+/cloud-access-role$", mcp_type=MCPType.TOOL),
    
    # Exclude all other routes
    RouteMap(mcp_type=MCPType.EXCLUDE),
]