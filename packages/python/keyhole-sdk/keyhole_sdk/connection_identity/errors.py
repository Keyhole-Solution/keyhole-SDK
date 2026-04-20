"""SDK-CLIENT-01-C — Connection identity errors with repair guidance (§16).

Typed error classes for connection identity operations.  Each error
carries a reason and concrete repair suggestions for CLI rendering.
"""
from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.exceptions import KeyholeSDKError


class ConnectionIdentityError(KeyholeSDKError):
    """Base error for connection identity operations."""

    error_class: str = "connection_identity_error"

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


class ConnectionNotFoundError(ConnectionIdentityError):
    """Connection not visible from the server (§16.3)."""

    error_class = "host_connection_not_visible"

    def __init__(
        self,
        message: str = "Connection not visible from server.",
        *,
        host_id: str = "",
        connection_id: str = "",
    ) -> None:
        super().__init__(
            message,
            reason=f"Connection for host '{host_id or connection_id}' not visible.",
            repair_suggestions=[
                "Ensure the host has opened a Keyhole connection.",
                "Refresh the host and retry.",
                "Run 'keyhole connections list' to see visible connections.",
            ],
        )
        self.host_id = host_id
        self.connection_id = connection_id


class ConnectionNetworkError(ConnectionIdentityError):
    """Network failure during connection identity operation."""

    error_class = "connection_network_error"

    def __init__(self, message: str = "Network error.") -> None:
        super().__init__(
            message,
            reason="Failed to reach the MCP boundary.",
            repair_suggestions=[
                "Check network connectivity.",
                "Verify the MCP URL is correct.",
                "Run 'keyhole doctor' to check environment health.",
            ],
        )


class ConnectionSurfaceUnavailableError(ConnectionIdentityError):
    """Server does not support connection-truth surfaces (§16.5)."""

    error_class = "host_rebind_unsupported"

    def __init__(
        self,
        message: str = "Connection surfaces not available on server.",
        *,
        surface: str = "",
    ) -> None:
        super().__init__(
            message,
            reason=f"Server does not support surface '{surface}'.",
            repair_suggestions=[
                "Upgrade the server to a version that supports connection surfaces.",
                "Use 'keyhole whoami' for generic identity inspection.",
                "Invalidate the connection and reconnect under the desired profile.",
            ],
        )
        self.surface = surface


class RebindRejectedError(ConnectionIdentityError):
    """Server rejected the rebind request (§16.6)."""

    error_class = "host_rebind_rejected"

    def __init__(
        self,
        message: str = "Rebind rejected by server.",
        *,
        server_reason: str = "",
    ) -> None:
        super().__init__(
            message,
            reason=server_reason or "The server rejected the rebind request.",
            repair_suggestions=[
                "Inspect the server's rejection reason.",
                "Verify the target profile and session are valid.",
                "Retry with a valid identity.",
            ],
        )
        self.server_reason = server_reason


class VerificationFailedError(ConnectionIdentityError):
    """Post-fix verification failed (§16.7)."""

    error_class = "host_verification_failed"

    def __init__(
        self,
        message: str = "Post-fix verification failed.",
        *,
        expected_principal: str = "",
        actual_principal: str = "",
    ) -> None:
        super().__init__(
            message,
            reason=(
                f"Expected principal '{expected_principal}' but server reports "
                f"'{actual_principal}'."
            ),
            repair_suggestions=[
                "Rerun 'keyhole connection whoami' to inspect current state.",
                "Check the support bundle for details.",
                "Do not assume the fix was applied.",
            ],
        )
        self.expected_principal = expected_principal
        self.actual_principal = actual_principal


class ConnectionNotAuthenticatedError(ConnectionIdentityError):
    """Not authenticated for connection identity operations."""

    error_class = "connection_not_authenticated"

    def __init__(self, message: str = "Not authenticated.") -> None:
        super().__init__(
            message,
            reason="No valid authentication session found.",
            repair_suggestions=[
                "Run 'keyhole login' first.",
                "Run 'keyhole login --flow passwordless' for email-based login.",
            ],
        )
