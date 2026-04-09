"""Tests for OAuthManager."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from kion_mcp.config.oauth import OAuthManager


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
