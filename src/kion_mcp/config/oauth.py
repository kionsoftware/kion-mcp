"""OAuth Device Authorization Flow manager for Kion MCP Server."""

import json
import logging
import os
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

    def _oauth_url(self, path: str) -> str:
        """Build an OAuth endpoint URL at the server root (outside /api).

        OAuth endpoints live at the root of the Kion instance, e.g.:
          /device_authorization, /token, /authorize
        But server_base_url typically ends with /api, so we strip it.
        """
        base = self.config.server_base_url.rstrip("/")
        if base.endswith("/api"):
            base = base[:-4]
        return f"{base}{path}"

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
            fd = os.open(str(cache_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
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

    # ------------------------------------------------------------------
    # Device Authorization Flow
    # ------------------------------------------------------------------

    async def _request_device_authorization(self) -> dict:
        """Request device authorization from the OAuth server.
        POST /oauth/device_authorization with client_id and scopes.
        Returns dict with device_code, user_code, verification_uri, expires_in, interval.
        Raises AuthenticationError on failure.
        """
        url = self._oauth_url("/device_authorization")

        data = {
            "client_id": self.config.oauth_client_id,
            "scope": self.config.oauth_scopes,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, timeout=15)

        if response.status_code == 404:
            raise AuthenticationError(
                "OAuth is not enabled on this Kion instance. "
                "Use a bearer token or auth script instead."
            )

        if response.status_code != 200:
            try:
                err = response.json()
                error_code = err.get("error", "unknown")
                error_desc = err.get("error_description", response.text)
                raise AuthenticationError(
                    f"Device authorization failed: {error_code} — {error_desc}"
                )
            except (ValueError, KeyError):
                raise AuthenticationError(
                    f"Device authorization failed: HTTP {response.status_code} {response.text}"
                )

        return response.json()

    async def _poll_for_token(self, device_code: str, interval: int, expires_in: int) -> dict:
        """Poll the token endpoint until user approves or code expires.
        Returns dict with access_token, token_type, expires_in, and optionally refresh_token.
        Raises AuthenticationError on denial, expiry, or unexpected error.
        """
        import asyncio

        url = self._oauth_url("/token")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self.config.oauth_client_id,
        }

        deadline = time.time() + expires_in
        poll_interval = interval

        async with httpx.AsyncClient() as client:
            while time.time() < deadline:
                await asyncio.sleep(poll_interval)

                response = await client.post(url, data=data, timeout=15)

                try:
                    body = response.json()
                except ValueError:
                    raise AuthenticationError(
                        f"Unexpected response from token endpoint: {response.text}"
                    )

                error = body.get("error")
                if error:
                    if error == "authorization_pending":
                        continue
                    elif error == "slow_down":
                        poll_interval += 5
                        continue
                    elif error == "access_denied":
                        raise AuthenticationError("Authorization denied by user")
                    elif error == "expired_token":
                        raise AuthenticationError("Device code expired")
                    else:
                        desc = body.get("error_description", "")
                        raise AuthenticationError(f"Token error: {error} — {desc}")

                if body.get("access_token"):
                    return body

        raise AuthenticationError("Device code expired (polling deadline reached)")

    # ------------------------------------------------------------------
    # Token Refresh
    # ------------------------------------------------------------------

    async def _refresh_token(self, refresh_token: str) -> dict:
        """Exchange a refresh token for new tokens.
        POST /oauth/token with grant_type=refresh_token.
        Raises AuthenticationError on failure.
        """
        url = self._oauth_url("/token")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.oauth_client_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, timeout=15)

        try:
            body = response.json()
        except ValueError:
            raise AuthenticationError(
                f"Unexpected response from token endpoint: {response.text}"
            )

        if response.status_code != 200:
            error = body.get("error", "unknown")
            desc = body.get("error_description", "")
            raise AuthenticationError(f"Token refresh failed: {error} — {desc}")

        return body

    async def refresh_access_token(self) -> tuple[bool, str]:
        """Attempt to refresh the access token using a cached refresh token.
        Returns (True, new_access_token) on success, (False, error_message) on failure.
        """
        cache = self._load_token_cache()
        if not cache or not cache.get("refresh_token"):
            return False, "No refresh token available"

        refresh_expires = cache.get("refresh_token_expires_at", 0)
        if self._is_token_expired(refresh_expires):
            logging.info("Refresh token expired, clearing cache")
            self.clear_cached_tokens()
            return False, "Refresh token expired"

        try:
            token_data = await self._refresh_token(cache["refresh_token"])
            access_token = token_data["access_token"]
            new_refresh = token_data.get("refresh_token", cache["refresh_token"])
            expires_in = token_data.get("expires_in", 3600)

            self._save_token_cache(access_token, new_refresh, expires_in)
            logging.info("Access token refreshed successfully")
            return True, access_token

        except AuthenticationError as exc:
            logging.warning("Token refresh failed: %s", exc)
            self.clear_cached_tokens()
            return False, str(exc)

    # ------------------------------------------------------------------
    # Browser Launch
    # ------------------------------------------------------------------

    @staticmethod
    def _open_browser(url: str) -> bool:
        """Attempt to open a URL in the system browser.
        Returns True if the browser command was launched.
        """
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.Popen(["open", url])
            elif system == "Linux":
                subprocess.Popen(["xdg-open", url])
            elif system == "Windows":
                subprocess.Popen(["rundll32", "url.dll,FileProtocolHandler", url])
            else:
                logging.warning("Unknown OS %s, cannot open browser", system)
                return False
            return True
        except OSError as exc:
            logging.warning("Failed to open browser: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Full Device Flow & Main Entry Point
    # ------------------------------------------------------------------

    async def run_device_flow(self, ctx=None) -> tuple[bool, str]:
        """Run the full OAuth device authorization flow.
        Shows user code via elicitation and opens browser.
        Polls until user approves or code expires.
        Returns (True, access_token) on success, (False, error_message) on failure.
        """
        from ..interaction.elicitation import elicit_device_code_approval

        try:
            device_resp = await self._request_device_authorization()
        except AuthenticationError as exc:
            return False, str(exc)

        user_code = device_resp["user_code"]
        device_code = device_resp["device_code"]
        interval = device_resp.get("interval", 5)
        expires_in = device_resp.get("expires_in", 900)

        verification_url = device_resp.get("verification_uri_complete") or device_resp.get("verification_uri", "")
        if not verification_url:
            verification_url = self._oauth_url(f"/oauth/device?user_code={user_code}")

        # For local dev: the OAuth server returns the API port (8081) but
        # the device approval page is served by the frontend (8080).
        browser_url = verification_url.replace(":8081", ":8080")

        browser_opened = self._open_browser(browser_url)

        if ctx:
            await elicit_device_code_approval(ctx, user_code, verification_url)
        elif not browser_opened:
            logging.warning(
                "OAuth device flow: visit %s and enter code %s",
                verification_url, user_code,
            )

        try:
            token_data = await self._poll_for_token(device_code, interval, expires_in)
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            token_expires_in = token_data.get("expires_in", 3600)

            self._save_token_cache(access_token, refresh_token, token_expires_in)
            logging.info("Device flow authentication successful")
            return True, access_token

        except AuthenticationError as exc:
            self.clear_cached_tokens()
            return False, str(exc)

    async def get_access_token(self, ctx=None) -> str:
        """Get a valid access token, using cache, refresh, or device flow.
        This is the main entry point for obtaining an OAuth token.
        Follows the chain: cached token -> refresh token -> device flow.
        Raises AuthenticationError if all methods fail.
        """
        # Step 1: Check for a valid cached access token
        cache = self._load_token_cache()
        if cache and cache.get("access_token"):
            expires_at = cache.get("access_token_expires_at", 0)
            if not self._is_token_expired(expires_at):
                logging.info("Using cached access token")
                return cache["access_token"]

        # Step 2: Try refresh token
        success, token_or_msg = await self.refresh_access_token()
        if success:
            return token_or_msg

        # Step 3: Fall back to device flow
        logging.info("Falling back to device authorization flow")
        success, token_or_msg = await self.run_device_flow(ctx)
        if success:
            return token_or_msg

        raise AuthenticationError(f"OAuth authentication failed: {token_or_msg}")
