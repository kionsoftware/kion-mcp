"""Tests for KionConfig OAuth fields."""

import os
import pytest
import yaml
from unittest.mock import patch
from kion_mcp.config.settings import KionConfig


class TestOAuthConfigFields:
    """Test oauth_client_id and oauth_scopes on KionConfig."""

    def test_default_oauth_fields_are_none(self, base_config):
        config = KionConfig()
        assert config.oauth_client_id is None
        assert config.oauth_scopes == "openid offline_access"

    def test_is_oauth_mode_when_client_id_set(self, oauth_config):
        assert oauth_config.is_oauth_mode() is True

    def test_is_oauth_mode_when_client_id_not_set(self, base_config):
        assert base_config.is_oauth_mode() is False

    def test_needs_configuration_false_with_oauth(self, oauth_config):
        assert oauth_config.needs_configuration() is False

    def test_oauth_from_environment(self):
        env = {
            "KION_SERVER_URL": "https://kion.example.com",
            "KION_OAUTH_CLIENT_ID": "env-client-id",
            "KION_OAUTH_SCOPES": "openid",
        }
        with patch.dict(os.environ, env, clear=False):
            config = KionConfig()
            config._load_from_environment()
            assert config.oauth_client_id == "env-client-id"
            assert config.oauth_scopes == "openid"

    def test_oauth_from_environment_default_scopes(self):
        env = {
            "KION_SERVER_URL": "https://kion.example.com",
            "KION_OAUTH_CLIENT_ID": "env-client-id",
        }
        with patch.dict(os.environ, env, clear=False):
            config = KionConfig()
            config._load_from_environment()
            assert config.oauth_client_id == "env-client-id"
            assert config.oauth_scopes == "openid offline_access"

    def test_oauth_from_yaml_file(self, tmp_path):
        config_file = tmp_path / "kion_mcp_config.yaml"
        config_file.write_text(yaml.dump({
            "server_base_url": "https://kion.example.com",
            "oauth_client_id": "yaml-client-id",
            "oauth_scopes": "openid offline_access profile",
        }))
        config = KionConfig()
        config._config_path = config_file
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
        config.server_base_url = config._process_server_url(config_data.get("server_base_url"))
        config.oauth_client_id = config_data.get("oauth_client_id")
        config.oauth_scopes = config_data.get("oauth_scopes", "openid offline_access")
        assert config.oauth_client_id == "yaml-client-id"
        assert config.oauth_scopes == "openid offline_access profile"

    def test_save_includes_oauth_fields(self, tmp_path, oauth_config):
        config_file = tmp_path / "kion_mcp_config.yaml"
        oauth_config._config_path = config_file
        oauth_config.save()
        with open(config_file, "r") as f:
            saved = yaml.safe_load(f)
        assert saved["oauth_client_id"] == "test-client-id"
        assert saved["oauth_scopes"] == "openid offline_access"
