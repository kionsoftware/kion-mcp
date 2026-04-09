"""Tests for AuthManager OAuth integration and priority chain."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from kion_mcp.config.auth import AuthManager
from kion_mcp.config.oauth import OAuthManager
from kion_mcp.exceptions import AuthenticationError


class TestAuthPriority:
    """Test auth method priority: bearer > OAuth > script."""

    def test_bearer_token_wins_over_oauth(self, base_config):
        base_config.bearer_token = "static-token"
        base_config.oauth_client_id = "client-id"
        mgr = AuthManager(base_config)
        token = mgr.get_bearer_token()
        assert token == "static-token"

    def test_oauth_used_when_no_bearer(self, oauth_config):
        oauth_config.bearer_token = None
        mgr = AuthManager(oauth_config)
        with patch.object(OAuthManager, 'get_access_token', new_callable=AsyncMock, return_value="oauth-token"):
            # get_bearer_token is sync, but OAuth is async — the sync path
            # should return None so that async callers use get_bearer_token_async
            # For now, verify the OAuthManager is created
            assert mgr._oauth_manager is not None

    def test_script_auth_used_when_no_oauth(self, script_config):
        mgr = AuthManager(script_config)
        assert mgr._oauth_manager is None
        # Script auth tested elsewhere

    def test_no_oauth_manager_without_client_id(self, base_config):
        mgr = AuthManager(base_config)
        assert mgr._oauth_manager is None


class TestAuthManagerOAuthRefresh:
    """Test refresh_bearer_token_with_elicitation with OAuth."""

    @pytest.mark.asyncio
    async def test_oauth_refresh_delegates_to_oauth_manager(self, oauth_config):
        oauth_config.bearer_token = None
        mgr = AuthManager(oauth_config)
        with patch.object(mgr._oauth_manager, 'refresh_access_token', new_callable=AsyncMock, return_value=(True, "refreshed")):
            success, token = await mgr.refresh_bearer_token_with_elicitation()
            assert success is True
            assert token == "refreshed"

    @pytest.mark.asyncio
    async def test_oauth_refresh_falls_back_to_device_flow(self, oauth_config):
        oauth_config.bearer_token = None
        mgr = AuthManager(oauth_config)
        with patch.object(mgr._oauth_manager, 'refresh_access_token', new_callable=AsyncMock, return_value=(False, "expired")):
            with patch.object(mgr._oauth_manager, 'run_device_flow', new_callable=AsyncMock, return_value=(True, "device-token")):
                success, token = await mgr.refresh_bearer_token_with_elicitation()
                assert success is True
                assert token == "device-token"

    @pytest.mark.asyncio
    async def test_oauth_refresh_returns_failure_when_all_fail(self, oauth_config):
        oauth_config.bearer_token = None
        mgr = AuthManager(oauth_config)
        with patch.object(mgr._oauth_manager, 'refresh_access_token', new_callable=AsyncMock, return_value=(False, "expired")):
            with patch.object(mgr._oauth_manager, 'run_device_flow', new_callable=AsyncMock, return_value=(False, "denied")):
                success, msg = await mgr.refresh_bearer_token_with_elicitation()
                assert success is False
