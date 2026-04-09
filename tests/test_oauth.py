"""Tests for OAuthManager."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from kion_mcp.config.oauth import OAuthManager
from kion_mcp.exceptions import AuthenticationError


def _mock_async_client(*responses):
    """Create a mock httpx.AsyncClient context manager that returns canned responses.

    Each call to client.post() returns the next response in the list.
    If only one response is provided, it's returned for every call.
    """
    mock_client = AsyncMock()
    if len(responses) == 1:
        mock_client.post.return_value = responses[0]
    else:
        mock_client.post.side_effect = list(responses)

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_client
    cm.__aexit__.return_value = False
    return cm, mock_client


class TestTokenCache:
    """Test token cache file operations."""

    def test_save_and_load_token_cache(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            mgr._save_token_cache(
                access_token="access123",
                refresh_token="refresh456",
                access_expires_in=3600,
            )
            cache = mgr._load_token_cache()
            assert cache is not None
            assert cache["access_token"] == "access123"
            assert cache["refresh_token"] == "refresh456"
            assert cache["server_url"] == "https://kion.example.com/api"

    def test_load_cache_returns_none_when_missing(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            assert mgr._load_token_cache() is None

    def test_load_cache_returns_none_on_server_url_mismatch(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://other-kion.example.com/api",
            "access_token": "old-token",
            "access_token_expires_at": time.time() + 3600,
            "refresh_token": "old-refresh",
            "refresh_token_expires_at": time.time() + 86400,
        }))
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            assert mgr._load_token_cache() is None

    def test_load_cache_returns_none_on_corrupt_file(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text("not valid json{{{")
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            assert mgr._load_token_cache() is None

    def test_is_token_expired_false_for_future(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        assert mgr._is_token_expired(time.time() + 3600) is False

    def test_is_token_expired_true_for_past(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        assert mgr._is_token_expired(time.time() - 10) is True

    def test_is_token_expired_true_within_buffer(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        # 15 seconds from now is within 30-second buffer
        assert mgr._is_token_expired(time.time() + 15) is True

    def test_clear_cached_tokens(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text("{}")
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            mgr.clear_cached_tokens()
            assert not cache_file.exists()

    def test_cache_file_permissions(self, tmp_path, oauth_config):
        """Token cache file should be readable only by the owner (0600)."""
        import os
        import stat
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            mgr._save_token_cache("tok", "ref", 3600)
            mode = os.stat(cache_file).st_mode
            assert stat.S_IMODE(mode) == 0o600


class TestDeviceFlow:
    """Test device authorization request and token polling."""

    @pytest.mark.asyncio
    async def test_request_device_authorization_success(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_code": "device123",
            "user_code": "ABCD-EFGH",
            "verification_uri": "https://kion.example.com/oauth/device",
            "verification_uri_complete": "https://kion.example.com/oauth/device?user_code=ABCD-EFGH",
            "expires_in": 900,
            "interval": 5,
        }
        cm, _ = _mock_async_client(mock_response)
        with patch("httpx.AsyncClient", return_value=cm):
            result = await mgr._request_device_authorization()
            assert result["device_code"] == "device123"
            assert result["user_code"] == "ABCD-EFGH"

    @pytest.mark.asyncio
    async def test_request_device_authorization_404_oauth_not_enabled(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        cm, _ = _mock_async_client(mock_response)
        with patch("httpx.AsyncClient", return_value=cm):
            with pytest.raises(AuthenticationError, match="OAuth is not enabled"):
                await mgr._request_device_authorization()

    @pytest.mark.asyncio
    async def test_request_device_authorization_error_response(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Unknown client ID",
        }
        cm, _ = _mock_async_client(mock_response)
        with patch("httpx.AsyncClient", return_value=cm):
            with pytest.raises(AuthenticationError, match="invalid_client"):
                await mgr._request_device_authorization()

    @pytest.mark.asyncio
    async def test_poll_for_token_success_after_pending(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        pending_response = MagicMock()
        pending_response.status_code = 400
        pending_response.json.return_value = {"error": "authorization_pending"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "access_token": "access-token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh-token-456",
        }

        cm, _ = _mock_async_client(pending_response, success_response)
        with patch("httpx.AsyncClient", return_value=cm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await mgr._poll_for_token("device123", interval=5, expires_in=900)
                assert result["access_token"] == "access-token-123"
                assert result["refresh_token"] == "refresh-token-456"

    @pytest.mark.asyncio
    async def test_poll_for_token_access_denied(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        denied_response = MagicMock()
        denied_response.status_code = 400
        denied_response.json.return_value = {"error": "access_denied"}

        cm, _ = _mock_async_client(denied_response)
        with patch("httpx.AsyncClient", return_value=cm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AuthenticationError, match="denied"):
                    await mgr._poll_for_token("device123", interval=5, expires_in=900)

    @pytest.mark.asyncio
    async def test_poll_for_token_expired(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        expired_response = MagicMock()
        expired_response.status_code = 400
        expired_response.json.return_value = {"error": "expired_token"}

        cm, _ = _mock_async_client(expired_response)
        with patch("httpx.AsyncClient", return_value=cm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AuthenticationError, match="expired"):
                    await mgr._poll_for_token("device123", interval=5, expires_in=900)

    @pytest.mark.asyncio
    async def test_poll_for_token_slow_down(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        slow_response = MagicMock()
        slow_response.status_code = 400
        slow_response.json.return_value = {"error": "slow_down"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "access_token": "access-token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        cm, mock_client = _mock_async_client(slow_response, success_response)
        sleep_mock = AsyncMock()
        with patch("httpx.AsyncClient", return_value=cm):
            with patch("asyncio.sleep", sleep_mock):
                result = await mgr._poll_for_token("device123", interval=5, expires_in=900)
                # First sleep should be 5s (original), second should be 10s (5+5 slow_down)
                assert sleep_mock.call_args_list[1][0][0] == 10


class TestTokenRefresh:
    """Test refresh token exchange."""

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://kion.example.com/api",
            "access_token": "old-access",
            "access_token_expires_at": time.time() - 100,
            "refresh_token": "valid-refresh",
            "refresh_token_expires_at": time.time() + 86400,
        }))

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "access_token": "new-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh-token",
        }

        cm, _ = _mock_async_client(success_response)
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            with patch("httpx.AsyncClient", return_value=cm):
                success, token = await mgr.refresh_access_token()
                assert success is True
                assert token == "new-access-token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_no_refresh_token(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            success, msg = await mgr.refresh_access_token()
            assert success is False

    @pytest.mark.asyncio
    async def test_refresh_access_token_expired_refresh(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://kion.example.com/api",
            "access_token": "old-access",
            "access_token_expires_at": time.time() - 100,
            "refresh_token": "expired-refresh",
            "refresh_token_expires_at": time.time() - 100,
        }))
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            success, msg = await mgr.refresh_access_token()
            assert success is False

    @pytest.mark.asyncio
    async def test_refresh_access_token_server_error(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://kion.example.com/api",
            "access_token": "old-access",
            "access_token_expires_at": time.time() - 100,
            "refresh_token": "valid-refresh",
            "refresh_token_expires_at": time.time() + 86400,
        }))

        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"error": "invalid_grant"}

        cm, _ = _mock_async_client(error_response)
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            with patch("httpx.AsyncClient", return_value=cm):
                success, msg = await mgr.refresh_access_token()
                assert success is False


class TestBrowserAndElicitation:
    """Test browser launch and device code elicitation."""

    def test_open_browser_attempts_open_on_darwin(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value.poll.return_value = None
                result = mgr._open_browser("https://example.com/oauth/device?code=ABCD")
                mock_popen.assert_called_once()
                assert "open" in mock_popen.call_args[0][0]

    def test_open_browser_attempts_xdg_open_on_linux(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value.poll.return_value = None
                result = mgr._open_browser("https://example.com/oauth/device?code=ABCD")
                mock_popen.assert_called_once()
                assert "xdg-open" in mock_popen.call_args[0][0]

    def test_open_browser_returns_false_on_error(self, oauth_config):
        mgr = OAuthManager(oauth_config)
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.Popen", side_effect=OSError("no browser")):
                result = mgr._open_browser("https://example.com")
                assert result is False


class TestGetAccessToken:
    """Test the main get_access_token entry point."""

    @pytest.mark.asyncio
    async def test_returns_cached_valid_token(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://kion.example.com/api",
            "access_token": "cached-token",
            "access_token_expires_at": time.time() + 3600,
            "refresh_token": "refresh",
            "refresh_token_expires_at": time.time() + 86400,
        }))
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            token = await mgr.get_access_token()
            assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        cache_file.write_text(json.dumps({
            "server_url": "https://kion.example.com/api",
            "access_token": "expired-token",
            "access_token_expires_at": time.time() - 100,
            "refresh_token": "valid-refresh",
            "refresh_token_expires_at": time.time() + 86400,
        }))

        refresh_response = MagicMock()
        refresh_response.status_code = 200
        refresh_response.json.return_value = {
            "access_token": "refreshed-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh",
        }

        cm, _ = _mock_async_client(refresh_response)
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            with patch("httpx.AsyncClient", return_value=cm):
                token = await mgr.get_access_token()
                assert token == "refreshed-token"

    @pytest.mark.asyncio
    async def test_falls_through_to_device_flow(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        # No cache file — should trigger device flow

        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            with patch.object(mgr, 'run_device_flow', new_callable=AsyncMock, return_value=(True, "device-token")):
                token = await mgr.get_access_token()
                assert token == "device-token"

    @pytest.mark.asyncio
    async def test_raises_when_all_methods_fail(self, tmp_path, oauth_config):
        cache_file = tmp_path / ".kion_mcp_token_cache.json"
        with patch.object(OAuthManager, '_cache_file_path', return_value=cache_file):
            mgr = OAuthManager(oauth_config)
            with patch.object(mgr, 'run_device_flow', new_callable=AsyncMock, return_value=(False, "flow failed")):
                with pytest.raises(AuthenticationError, match="flow failed"):
                    await mgr.get_access_token()
