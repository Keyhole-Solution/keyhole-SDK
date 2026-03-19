"""Authentication bootstrap errors — deterministic failure classes.

Every failure produces a class, reason, and repair guidance.
"""

from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.exceptions import KeyholeSDKError


class AuthBootstrapError(KeyholeSDKError):
    """Base error for auth bootstrap failures."""

    error_class: str = "auth_bootstrap_error"

    def __init__(
        self,
        message: str,
        *,
        reason: Optional[str] = None,
        repair_suggestions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason or message
        self.repair_suggestions = repair_suggestions or []


class NetworkError(AuthBootstrapError):
    """Network/connectivity failure during auth flow."""

    error_class = "network_error"

    def __init__(self, message: str = "Network connectivity failure") -> None:
        super().__init__(
            message,
            reason="Could not reach the authentication server.",
            repair_suggestions=[
                "Check network connectivity.",
                "Verify the auth server URL is correct.",
                "Try again in a few moments.",
            ],
        )


class BrowserLaunchError(AuthBootstrapError):
    """Browser could not be opened for PKCE flow."""

    error_class = "browser_launch_error"

    def __init__(self, message: str = "Could not open browser for login") -> None:
        super().__init__(
            message,
            reason="Browser launch failed — headless or restricted environment detected.",
            repair_suggestions=[
                "Use device flow instead: keyhole login --flow device",
                "Open the displayed URL manually in a browser.",
                "Set BROWSER environment variable to your browser path.",
            ],
        )


class ExpiredChallengeError(AuthBootstrapError):
    """Auth challenge (PKCE state or device code) has expired."""

    error_class = "expired_challenge"

    def __init__(self, message: str = "Authentication challenge expired") -> None:
        super().__init__(
            message,
            reason="The login challenge timed out before completion.",
            repair_suggestions=[
                "Retry login: keyhole login",
                "Complete the browser step more quickly.",
            ],
        )


class InvalidTokenError(AuthBootstrapError):
    """Completion token or auth code is invalid."""

    error_class = "invalid_token"

    def __init__(self, message: str = "Invalid authentication token received") -> None:
        super().__init__(
            message,
            reason="The authorization code or token was rejected by the server.",
            repair_suggestions=[
                "Retry login: keyhole login",
                "Ensure you completed the correct browser window.",
                "Clear local session and retry: keyhole login --force",
            ],
        )


class LoginDeniedError(AuthBootstrapError):
    """Login was explicitly denied by the auth server."""

    error_class = "login_denied"

    def __init__(self, message: str = "Login denied by authentication server") -> None:
        super().__init__(
            message,
            reason="The authentication server denied the login request.",
            repair_suggestions=[
                "Verify your account credentials.",
                "Contact your organization admin if access was revoked.",
            ],
        )


class CredentialStoreError(AuthBootstrapError):
    """Failed to read or write the local credential store."""

    error_class = "credential_store_error"

    def __init__(self, message: str = "Credential store operation failed") -> None:
        super().__init__(
            message,
            reason="Could not read from or write to the local credential store.",
            repair_suggestions=[
                "Check file permissions in ~/.keyhole/",
                "Clear the credential store: rm -rf ~/.keyhole/credentials.json",
                "Retry login: keyhole login",
            ],
        )


class WhoamiVerificationError(AuthBootstrapError):
    """Whoami call failed after successful token acquisition."""

    error_class = "whoami_verification_error"

    def __init__(self, message: str = "Identity verification failed after login") -> None:
        super().__init__(
            message,
            reason="Token was issued but identity verification via whoami failed.",
            repair_suggestions=[
                "Retry login: keyhole login",
                "Check that the MCP server is reachable.",
                "Clear local session and retry: keyhole login --force",
            ],
        )


class IncompleteIdentityError(AuthBootstrapError):
    """Server returned identity missing required governed fields."""

    error_class = "incomplete_identity"

    def __init__(self, message: str = "Server returned incomplete identity", *, missing_fields: list[str] | None = None) -> None:
        detail = message
        if missing_fields:
            detail = f"{message}: missing {', '.join(missing_fields)}"
        super().__init__(
            detail,
            reason="The /whoami response is missing required governed identity fields.",
            repair_suggestions=[
                "Retry login: keyhole login --force",
                "Contact your organization admin — your account may not be fully provisioned.",
                "Check that the MCP server is running a compatible version.",
            ],
        )
        self.missing_fields = missing_fields or []
