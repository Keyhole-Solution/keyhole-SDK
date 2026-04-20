"""Passwordless authentication flow — email code-based login.

Flow:
  1. POST /auth/login-request with email + realm
  2. Server sends 6-digit code to verified email
  3. User enters code
  4. POST /auth/login-complete with code (+ optional user_id)
  5. Server returns access_token + refresh_token
  6. Build TokenResponse for the auth bootstrap client
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from keyhole_sdk.auth_bootstrap.errors import (
    AuthBootstrapError,
    InvalidTokenError,
    NetworkError,
)
from keyhole_sdk.auth_bootstrap.models import TokenResponse


class PasswordlessLoginResponse:
    """Parsed response from POST /auth/login-request."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.user_id: str = data.get("user_id", "")
        self.email: str = data.get("email", "")
        self.realm: str = data.get("realm", "")
        self.code_sent: bool = data.get("code_sent", False)
        self.login_hint: str = data.get("login_hint", "")
        self.expires_in_seconds: int = data.get("expires_in_seconds", 600)


class PasswordlessFlow:
    """Passwordless email-code authentication flow.

    Calls the server's /auth/login-request and /auth/login-complete
    REST endpoints to authenticate without a password.
    """

    def __init__(
        self,
        mcp_base_url: str,
        *,
        timeout: int = 30,
    ) -> None:
        self._base_url = mcp_base_url.rstrip("/")
        self._timeout = timeout

    def request_code(
        self,
        email: str,
        realm: str = "kh-prod",
        *,
        idempotency_key: Optional[str] = None,
    ) -> PasswordlessLoginResponse:
        """Request a login code be sent to the user's email.

        Args:
            email: Verified email address.
            realm: Keycloak realm (default: kh-prod).
            idempotency_key: Optional idempotency key for the request.

        Returns:
            PasswordlessLoginResponse with user_id and login_hint.

        Raises:
            NetworkError: Cannot reach the server.
            AuthBootstrapError: Server rejected the request.
        """
        url = f"{self._base_url}/auth/login-request"
        payload = {"email": email, "realm": realm}
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=self._timeout
            )
        except requests.ConnectionError as exc:
            raise NetworkError(
                f"Cannot reach login-request endpoint: {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise NetworkError(
                f"Login-request endpoint timed out: {exc}"
            ) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise NetworkError(
                "Login-request response is not valid JSON"
            ) from exc

        if resp.status_code == 429:
            detail = data.get("detail", "Rate limited")
            raise AuthBootstrapError(
                f"Rate limited: {detail}",
                reason="rate_limit_exceeded",
                repair_suggestions=["Wait a moment and try again."],
            )

        if resp.status_code != 200:
            # Server returns error shape in response body
            error = data.get("error", {}) if isinstance(data, dict) else {}
            detail = data.get("detail", "") if isinstance(data, dict) else str(data)
            msg = error.get("message", detail) if isinstance(error, dict) else detail
            raise AuthBootstrapError(
                msg or f"Login request failed (HTTP {resp.status_code})",
                reason=error.get("code", "login_request_failed") if isinstance(error, dict) else "login_request_failed",
                repair_suggestions=[
                    "Ensure the email is registered and verified.",
                    "Try: keyhole register (if not yet registered).",
                ],
            )

        return PasswordlessLoginResponse(data)

    def complete_login(
        self,
        code: str,
        *,
        user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> TokenResponse:
        """Complete passwordless login by submitting the 6-digit code.

        Args:
            code: The 6-digit code from email.
            user_id: Optional user_id hint (from request_code response).
            idempotency_key: Optional idempotency key.

        Returns:
            TokenResponse with access_token and refresh_token.

        Raises:
            NetworkError: Cannot reach the server.
            InvalidTokenError: Code is invalid or expired.
        """
        url = f"{self._base_url}/auth/login-complete"
        payload: Dict[str, Any] = {"code": code}
        if user_id:
            payload["user_id"] = user_id
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=self._timeout
            )
        except requests.ConnectionError as exc:
            raise NetworkError(
                f"Cannot reach login-complete endpoint: {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise NetworkError(
                f"Login-complete endpoint timed out: {exc}"
            ) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise NetworkError(
                "Login-complete response is not valid JSON"
            ) from exc

        if resp.status_code != 200:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            detail = data.get("detail", "") if isinstance(data, dict) else str(data)
            msg = error.get("message", detail) if isinstance(error, dict) else detail
            raise InvalidTokenError(
                msg or f"Login completion failed (HTTP {resp.status_code})"
            )

        # Build TokenResponse from the server's login-complete response
        return TokenResponse(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
        )
