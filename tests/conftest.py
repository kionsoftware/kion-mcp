"""Shared test fixtures for kion-mcp tests."""

import pytest
from kion_mcp.config.settings import KionConfig


@pytest.fixture
def base_config():
    """Create a KionConfig with minimal valid settings."""
    config = KionConfig()
    config.server_base_url = "https://kion.example.com/api"
    return config


@pytest.fixture
def oauth_config(base_config):
    """Create a KionConfig with OAuth settings."""
    base_config.oauth_client_id = "test-client-id"
    base_config.oauth_scopes = "openid offline_access"
    return base_config


@pytest.fixture
def bearer_config(base_config):
    """Create a KionConfig with a static bearer token."""
    base_config.bearer_token = "test-bearer-token"
    return base_config


@pytest.fixture
def script_config(base_config):
    """Create a KionConfig with an auth script."""
    base_config.auth_script_path = "/usr/local/bin/get-token.sh"
    return base_config
