"""OAuth Device Authorization Flow manager for Kion MCP Server."""

import json
import logging
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx

from .settings import KionConfig
from ..exceptions import AuthenticationError

# Token expiry buffer — consider tokens expired 30 seconds early
_EXPIRY_BUFFER_SECONDS = 30

# Default refresh token lifetime estimate (30 days, portal default)
_DEFAULT_REFRESH_TOKEN_LIFETIME = 30 * 24 * 3600


class OAuthManager:
    """Manages OAuth Device Authorization Flow for Kion API."""

    def __init__(self, config: KionConfig):
        self.config = config

    @staticmethod
    def _cache_file_path() -> Path:
        """Return the path to the token cache file."""
        return Path.home() / ".kion_mcp_token_cache.json"

    def _load_token_cache(self) -> Optional[dict]:
        """Load and validate the token cache file.

        Returns None if the file is missing, corrupt, or belongs to a
        different server URL.
        """
        cache_path = self._cache_file_path()
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logging.warning("Token cache unreadable, ignoring: %s", exc)
            return None

        # Invalidate if server URL changed
        if cache.get("server_url") != self.config.server_base_url:
            logging.info("Token cache server_url mismatch, ignoring")
            return None

        return cache

    def _save_token_cache(
        self,
        access_token: str,
        refresh_token: Optional[str],
        access_expires_in: int,
    ) -> None:
        """Write tokens to the cache file with absolute expiry timestamps."""
        now = time.time()
        cache = {
            "server_url": self.config.server_base_url,
            "access_token": access_token,
            "access_token_expires_at": now + access_expires_in,
            "refresh_token": refresh_token,
            "refresh_token_expires_at": now + _DEFAULT_REFRESH_TOKEN_LIFETIME,
        }
        try:
            cache_path = self._cache_file_path()
            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)
            logging.info("Token cache saved to %s", cache_path)
        except OSError as exc:
            logging.warning("Failed to write token cache: %s", exc)

    @staticmethod
    def _is_token_expired(expiry_timestamp: float) -> bool:
        """Check if a token has expired (with buffer)."""
        return time.time() >= expiry_timestamp - _EXPIRY_BUFFER_SECONDS

    def clear_cached_tokens(self) -> None:
        """Remove the token cache file."""
        cache_path = self._cache_file_path()
        try:
            cache_path.unlink(missing_ok=True)
            logging.info("Token cache cleared")
        except OSError as exc:
            logging.warning("Failed to clear token cache: %s", exc)
