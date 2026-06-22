"""Behavior-based migration guard for tool enable/disable logic.

These tests assert on the *observable* set of client-visible tools (via the
in-memory ``Client`` listing in ``conftest.listed_tool_names``), never on
fastmcp internals. They must pass identically on fastmcp 2.x and on 3.x after
the migration refactors ``tool_manager`` to the public async tool API — that is
exactly the regression they guard.
"""

import pytest

from kion_mcp.server_management import tool_manager as tm
from kion_mcp.constants.tools import (
    ADD_PROJECT_SPEND_PLAN_ENTRIES,
    ALLOCATE_FUNDS,
    CHECK_CONFIG_STATUS,
    CONFIG_MODE_TOOLS,
    CREATE_BUDGET,
    CREATE_PROJECT_WITH_BUDGET,
    CREATE_PROJECT_WITH_SPEND_PLAN,
    GET_OU_BUDGET,
    GET_OUS,
    GET_PROJECT_BUDGET,
    GET_PROJECT_SPEND_PLAN_WITH_TOTALS,
    SETUP_KION_CONFIG,
)

# A representative mix: the two config-mode tools plus the API tools whose
# enabled state depends on app-config (budget / spend-plan / allocation).
API_TOOLS = [
    GET_OUS,
    CREATE_PROJECT_WITH_SPEND_PLAN,
    GET_PROJECT_SPEND_PLAN_WITH_TOTALS,
    ADD_PROJECT_SPEND_PLAN_ENTRIES,
    CREATE_PROJECT_WITH_BUDGET,
    CREATE_BUDGET,
    GET_OU_BUDGET,
    GET_PROJECT_BUDGET,
    ALLOCATE_FUNDS,
]
ALL_TOOLS = list(CONFIG_MODE_TOOLS) + API_TOOLS

SPEND_PLAN_TOOLS = {
    CREATE_PROJECT_WITH_SPEND_PLAN,
    GET_PROJECT_SPEND_PLAN_WITH_TOTALS,
    ADD_PROJECT_SPEND_PLAN_ENTRIES,
}
BUDGET_TOOLS = {CREATE_PROJECT_WITH_BUDGET, CREATE_BUDGET, GET_OU_BUDGET, GET_PROJECT_BUDGET}


async def test_disable_then_enable_roundtrip(make_server, listed_tool_names, call):
    mcp = make_server([GET_OUS, CREATE_BUDGET])
    assert await listed_tool_names(mcp) == {GET_OUS, CREATE_BUDGET}

    await call(tm.disable_tools, mcp, [CREATE_BUDGET])
    assert await listed_tool_names(mcp) == {GET_OUS}

    await call(tm.enable_tools, mcp, [CREATE_BUDGET])
    assert await listed_tool_names(mcp) == {GET_OUS, CREATE_BUDGET}


async def test_enable_disable_unknown_tool_is_noop(make_server, listed_tool_names, call):
    mcp = make_server([GET_OUS])
    # Should warn-and-skip, not raise, and not change the listing.
    await call(tm.disable_tools, mcp, ["does_not_exist"])
    await call(tm.enable_tools, mcp, ["also_missing"])
    assert await listed_tool_names(mcp) == {GET_OUS}


async def test_configure_config_mode_leaves_only_config_tools(make_server, listed_tool_names, call):
    mcp = make_server(ALL_TOOLS)
    await call(tm.configure_config_mode, mcp)
    assert await listed_tool_names(mcp) == set(CONFIG_MODE_TOOLS)


async def test_enable_all_operational_disables_config_tools(make_server, listed_tool_names, call):
    mcp = make_server(ALL_TOOLS)
    await call(tm.configure_config_mode, mcp)  # start from config mode

    await call(tm.enable_all_operational_tools, mcp)
    listed = await listed_tool_names(mcp)

    assert set(CONFIG_MODE_TOOLS).isdisjoint(listed)
    assert set(API_TOOLS).issubset(listed)


async def test_disable_based_on_config_budget_mode(make_server, listed_tool_names, call):
    mcp = make_server(ALL_TOOLS)
    await call(tm.enable_all_operational_tools, mcp)

    await call(tm.disable_tools_based_on_config, mcp, {"budget_mode": True, "allocation_mode": False})
    listed = await listed_tool_names(mcp)

    assert SPEND_PLAN_TOOLS.isdisjoint(listed)   # spend-plan tools disabled
    assert BUDGET_TOOLS.issubset(listed)         # budget tools remain
    assert ALLOCATE_FUNDS not in listed          # allocation_mode off


async def test_disable_based_on_config_spend_plan_mode(make_server, listed_tool_names, call):
    mcp = make_server(ALL_TOOLS)
    await call(tm.enable_all_operational_tools, mcp)

    await call(tm.disable_tools_based_on_config, mcp, {"budget_mode": False, "allocation_mode": True})
    listed = await listed_tool_names(mcp)

    assert BUDGET_TOOLS.isdisjoint(listed)       # budget tools disabled
    assert SPEND_PLAN_TOOLS.issubset(listed)     # spend-plan tools remain
    assert ALLOCATE_FUNDS in listed              # allocation_mode on
