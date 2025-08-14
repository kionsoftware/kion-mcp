"""Tool constants for Kion MCP Server.

This module contains mappings between OpenAPI operation IDs and readable tool names,
as well as referenceable constants for easy use in enable/disable operations.
"""

# Mapping from OpenAPI operation IDs to readable tool names
TOOL_NAME_MAPPING = {
    # Account tools
    "apiV1getAccountIndex": "get_accounts",
    
    # OU tools
    "apiV1getOUIndex": "get_ous", 
    "apiV1postOU": "create_ou",
    
    # Project tools
    "apiV1getProjectIndex": "get_projects",
    "apiV1postProjectWithBudgets": "create_project_with_budget",
    "apiV1postProjectWithSpendPlan": "create_project_with_spend_plan",
    
    # Budget tools
    "apiV1postBudget": "create_budget",
    "apiV1putBudget": "update_budget",
    "apiV1getBudgetByOUID": "get_ou_budget",
    "apiV1getBudgetByProjectID": "get_project_budget",

    # Spend plan tools
    "apiV1getFundingTotalsByProjectID": "get_project_spend_plan_with_totals",
    "apiV2postSpendPlan": "add_project_spend_plan_entries",
    
    # Funding and allocation tools
    "apiV1postFundingSource": "create_funding_source",
    "postAllocationPublicV1": "allocate_funds",
    "apiV1getOUFundingSources": "get_ou_funding_sources",
    
    # Permission tools
    "apiV1getPermissionSchemeByType": "get_permission_scheme",
    
    # Compliance tools
    "apiV1postComplianceCheck": "create_compliance_check",
    "apiV1getComplianceCheck": "get_compliance_check",
    "apiV1getComplianceOUs": "get_compliance_ous", 
    "apiV1getComplianceStandardProject": "get_compliance_standard_project",
    "apiV1getComplianceStandard": "get_compliance_standard",
    "apiV2getComplianceCheckPaginatedIndex": "get_compliance_checks_paginated",
    "apiV2getComplianceFindings": "get_compliance_findings",
    "apiV2getSuppressedComplianceFindings": "get_suppressed_compliance_findings",
    "apiV2getComplianceProgram": "get_compliance_program",
    "apiV2getComplianceStandardPaginatedIndex": "get_compliance_standards_paginated",
    
    # Cloud provider tools
    "apiV1getGetCloudProviders": "get_cloud_providers",
    "apiV1getCloudProvderServiceIndex": "get_cloud_provider_services",
    
    # Tag and label tools
    "apiV1getTagValues": "get_tag_values",
    "apiV1getTagKeys": "get_tag_keys", 
    "apiV1getLabelIndex": "get_labels",
    
    # User and user group tools
    "apiV1getUserIndex": "get_users",
    "apiV1getUGroupIndex": "get_user_groups",
    "apiV1getCARsByUserID": "get_user_cloud_access_roles",
}

# Referenceable constants for tool names
# Account tools
GET_ACCOUNTS = "get_accounts"

# OU tools  
GET_OUS = "get_ous"
CREATE_OU = "create_ou"

# Project tools
GET_PROJECTS = "get_projects"
CREATE_PROJECT_WITH_BUDGET = "create_project_with_budget"
CREATE_PROJECT_WITH_SPEND_PLAN = "create_project_with_spend_plan"

# Budget tools
CREATE_BUDGET = "create_budget"
UPDATE_BUDGET = "update_budget"
GET_OU_BUDGET = "get_ou_budget"
GET_PROJECT_BUDGET = "get_project_budget"

# Spend plan tools
GET_PROJECT_SPEND_PLAN_WITH_TOTALS = "get_project_spend_plan_with_totals"
ADD_PROJECT_SPEND_PLAN_ENTRIES = "add_project_spend_plan_entries"

# Funding and allocation tools
CREATE_FUNDING_SOURCE = "create_funding_source"
ALLOCATE_FUNDS = "allocate_funds"
GET_OU_FUNDING_SOURCES = "get_ou_funding_sources"

# Permission tools
GET_PERMISSION_SCHEME = "get_permission_scheme"

# Compliance tools
CREATE_COMPLIANCE_CHECK = "create_compliance_check"
GET_COMPLIANCE_CHECK = "get_compliance_check"
GET_COMPLIANCE_OUS = "get_compliance_ous"
GET_COMPLIANCE_STANDARD_PROJECT = "get_compliance_standard_project"
GET_COMPLIANCE_STANDARD = "get_compliance_standard"
GET_COMPLIANCE_CHECKS_PAGINATED = "get_compliance_checks_paginated"
GET_COMPLIANCE_FINDINGS = "get_compliance_findings"
GET_SUPPRESSED_COMPLIANCE_FINDINGS = "get_suppressed_compliance_findings"
GET_COMPLIANCE_PROGRAM = "get_compliance_program"
GET_COMPLIANCE_STANDARDS_PAGINATED = "get_compliance_standards_paginated"

# Cloud provider tools
GET_CLOUD_PROVIDERS = "get_cloud_providers"
GET_CLOUD_PROVIDER_SERVICES = "get_cloud_provider_services"

# Tag and label tools
GET_TAG_VALUES = "get_tag_values"
GET_TAG_KEYS = "get_tag_keys"
GET_LABELS = "get_labels"

# User and user group tools
GET_USERS = "get_users"
GET_USER_GROUPS = "get_user_groups"
GET_USER_CLOUD_ACCESS_ROLES = "get_user_cloud_access_roles"
GET_USER_INFO = "get_user_info"

# Cloud access role tools
GET_CLOUD_ACCESS_ROLES_ON_ENTITY = "get_cloud_access_roles_on_entity"
GET_CLOUD_ACCESS_ROLE_DETAILS = "get_cloud_access_role_details"

# Config mode tools
SETUP_KION_CONFIG = "setup_kion_config"
CHECK_CONFIG_STATUS = "check_config_status"

# List of all config mode tools
CONFIG_MODE_TOOLS = [
    SETUP_KION_CONFIG,
    CHECK_CONFIG_STATUS
]