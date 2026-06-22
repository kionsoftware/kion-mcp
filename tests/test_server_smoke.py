"""Construction smoke test for the full Kion MCP server.

Exercises the real ``create_full_server_async`` path (``from_openapi`` over the
bundled ``fixed_spec.json`` + custom-tool registration + mode configuration)
fully offline, by monkeypatching the network/auth touch points in
``tool_manager``.

This is the single test that reproduces, in CI, the breakages hit while doing
the fastmcp 2.x -> 3.x migration by hand: import paths, ``from_openapi``,
enable/disable, and the ``get_tool``/``remove_tool``/``add_tool`` description
path all run here.
"""

from kion_mcp.server import create_full_server_async
from kion_mcp.server_management import tool_manager as tm
from kion_mcp.constants.tools import (
    ALLOCATE_FUNDS,
    CONFIG_MODE_TOOLS,
    CREATE_PROJECT_WITH_SPEND_PLAN,
    GET_ACCOUNTS,
    GET_OUS,
    GET_USER_INFO,
)


async def test_constructs_in_config_mode(monkeypatch, listed_tool_names):
    monkeypatch.setattr(tm, "needs_configuration", lambda: True)

    mcp = await create_full_server_async()

    # Config mode exposes only the setup/status tools to clients.
    assert await listed_tool_names(mcp) == set(CONFIG_MODE_TOOLS)


async def test_constructs_in_operational_mode(monkeypatch, listed_tool_names):
    monkeypatch.setattr(tm, "needs_configuration", lambda: False)
    # Skip real auth / HTTP-client wiring (no network, no credentials).
    monkeypatch.setattr(
        tm,
        "setup_authentication_and_middleware",
        lambda mcp, client, config=None, auth_manager=None: (object(), object()),
    )

    async def fake_app_config():
        return {
            "budget_mode": True,
            "allocation_mode": False,
            "enforce_funding": False,
            "enforce_funding_sources": False,
        }

    monkeypatch.setattr(tm, "load_app_config_for_tools", fake_app_config)

    mcp = await create_full_server_async()
    listed = await listed_tool_names(mcp)

    # OpenAPI-derived tools and custom tools are exposed; config tools are hidden.
    assert GET_OUS in listed          # generated from the OpenAPI spec
    assert GET_USER_INFO in listed    # custom tool
    assert GET_ACCOUNTS in listed     # custom tool
    assert set(CONFIG_MODE_TOOLS).isdisjoint(listed)

    # budget_mode=True disables spend-plan tools; allocation_mode=False disables allocation.
    assert CREATE_PROJECT_WITH_SPEND_PLAN not in listed
    assert ALLOCATE_FUNDS not in listed

    # Description appends must land on OpenAPI-provider tools, not just custom
    # (local-provider) tools. Regression guard: the 3.x migration initially
    # applied these via the wrong provider, so they silently no-opped.
    funding_tool = await mcp.get_tool("create_funding_source")
    assert "top level ous" in (funding_tool.description or "")
