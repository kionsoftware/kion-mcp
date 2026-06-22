"""Shared fixtures for the kion-mcp test suite.

The fixtures here are deliberately version-agnostic across fastmcp 2.x and 3.x:

- ``listed_tool_names`` observes enabled/disabled state through the public,
  client-facing tool listing (disabled tools are excluded), which is stable
  across the 2.x -> 3.x migration. It never touches private internals like
  ``mcp._tool_manager._tools`` or the per-version ``Tool.enabled`` attribute.
- ``call`` invokes a tool-management function whether it is sync (2.x) or async
  (3.x), so the migration-guard tests do not change when those functions become
  ``async def`` during the migration.
"""

import inspect
import os

import pytest
from fastmcp import Client, FastMCP

# Route server logging to stderr (DXT mode) instead of creating a server_log.log
# file in the repo during test runs. Must be set before kion_mcp.server is first
# imported, since logging is configured at import time.
os.environ.setdefault("KION_DXT_MODE", "true")


@pytest.fixture
def call():
    """Return an invoker that awaits the result only if it is awaitable.

    Lets a single test call ``enable_tools``/``disable_tools``/etc. unchanged
    before (sync) and after (async) the fastmcp 3.x migration.
    """

    async def _call(fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    return _call


@pytest.fixture
def listed_tool_names():
    """Return an async helper giving the set of client-visible (enabled) tool names."""

    async def _names(mcp) -> set[str]:
        async with Client(mcp) as client:
            return {tool.name for tool in await client.list_tools()}

    return _names


@pytest.fixture
def make_server():
    """Return a factory building a FastMCP server with trivial named tools.

    Tools are registered by name only; the tool-management code under test
    operates purely on names, so the bodies are irrelevant.
    """

    def _make(tool_names) -> FastMCP:
        mcp = FastMCP(name="test-server")
        for name in tool_names:
            def _tool(_name=name) -> str:
                return _name

            mcp.tool(name=name)(_tool)
        return mcp

    return _make
