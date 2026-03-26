"""Device/constrained authentication flow — headless login support.

Implements §6.3 of SDK-CLIENT-01: Device/constrained flow support.

Flow:
  1. Discover OIDC endpoints from auth server
  2. Request device authorization from auth server
  3. Display user code and verification URI
  4. Poll token endpoint until user completes auth
  5. Return TokenResponse on success
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from keyhole_sdk.auth_bootstrap.errors import (
    ExpiredChallengeError,
    InvalidTokenError,
    LoginDeniedError,
    NetworkError,
)
from keyhole_sdk.auth_bootstrap.models import DeviceCodeResponse, TokenResponse


class DeviceFlow:
    """Device authorization flow for constrained/headless environments.

    This is the fallback path when browser-based PKCE is not available.
    Uses OIDC discovery to find correct endpoint paths.
    """

    def __init__(
        self,
        auth_server_url: str,
        client_id: str,
        *,
        scope: str = "openid profile email",
    ) -> None:
        self._auth_server_url = auth_server_url.rstrip("/")
        self._client_id = client_id
        self._scope = scope
        self._oidc_config: Optional[dict] = None

    def _discover_oidc(self) -> dict:
        """Fetch OIDC discovery document to find correct endpoints."""
        if self._oidc_config is not None:
            return self._oidc_config

        discovery_url = f"{self._auth_server_url}/.well-known/openid-configuration"
        try:
            resp = requests.get(discovery_url, timeout=30)
        except requests.ConnectionError as exc:
            raise NetworkError(f"Cannot reach OIDC discovery endpoint: {exc}") from exc
        except requests.Timeout as exc:
            raise NetworkError(f"OIDC discovery endpoint timed out: {exc}") from exc

        if resp.status_code != 200:
            raise NetworkError(
                f"OIDC discovery failed (HTTP {resp.status_code})"
            )

        try:
            self._oidc_config = resp.json()
        except ValueError as exc:
            raise NetworkError("OIDC discovery response is not valid JSON") from exc

        return self._oidc_config

    def request_device_code(self) -> DeviceCodeResponse:
        """Request a device code from the auth server."""
        oidc = self._discover_oidc()
        url = oidc.get("device_authorization_endpoint")
        if not url:
            # Fallback for servers without device flow in discovery
            url = f"{self._auth_server_url}/protocol/openid-connect/auth/device"
        payload = {
            "client_id": self._client_id,
            "scope": self._scope,
        }

        try:
            resp = requests.post(url, data=payload, timeout=30)
        except requests.ConnectionError as exc:
            raise NetworkError(f"Cannot reach device code endpoint: {exc}") from exc
        except requests.Timeout as exc:
            raise NetworkError(f"Device code endpoint timed out: {exc}") from exc

        if resp.status_code != 200:
            raise NetworkError(
                f"Device code request failed (HTTP {resp.status_code})"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise NetworkError("Device code response is not valid JSON") from exc

        return DeviceCodeResponse.model_validate(data)

    def poll_for_token(
        self,
        device_code: str,
        *,
        interval: int = 5,
        expires_in: int = 600,
        on_poll: Optional[callable] = None,
    ) -> TokenResponse:
        """Poll the token endpoint until the user completes device auth.

        Args:
            device_code: The device code from request_device_code()
            interval: Polling interval in seconds
            expires_in: Total timeout in seconds
            on_poll: Optional callback invoked each poll cycle
        """
        oidc = self._discover_oidc()
        url = oidc.get("token_endpoint")
        if not url:
            # Fallback for servers without token_endpoint in discovery
            url = f"{self._auth_server_url}/protocol/openid-connect/token"
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self._client_id,
        }

        deadline = time.monotonic() + expires_in

        while time.monotonic() < deadline:
            if on_poll:
                on_poll()

            try:
                resp = requests.post(url, data=payload, timeout=30)
            except requests.ConnectionError as exc:
                raise NetworkError(
                    f"Cannot reach token endpoint: {exc}"
                ) from exc
            except requests.Timeout:
                time.sleep(interval)
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise InvalidTokenError(
                        "Token response is not valid JSON"
                    ) from exc
                return TokenResponse.model_validate(data)

            # Handle standard OAuth2 device flow error responses
            try:
                error_data = resp.json()
            except ValueError:
                error_data = {}

            error = error_data.get("error", "")

            if error == "authorization_pending":
                time.sleep(interval)
                continue
            elif error == "slow_down":
                interval = min(interval + 5, 30)
                time.sleep(interval)
                continue
            elif error == "expired_token":
                raise ExpiredChallengeError()
            elif error == "access_denied":
                raise LoginDeniedError()
            else:
                raise InvalidTokenError(
                    f"Device token exchange failed: {error or resp.text[:200]}"
                )

        raise ExpiredChallengeError()
