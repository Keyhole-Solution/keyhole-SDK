"""SDK-CLIENT-22 — Deregistration errors.

Deterministic failure classes with repair guidance (§19).
"""

from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.exceptions import KeyholeSDKError


class DeregistrationError(KeyholeSDKError):
    """Base error for deregistration failures."""

    error_class: str = "deregistration_error"

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


class DeregistrationNotAuthenticatedError(DeregistrationError):
    """Builder is not authenticated — §19."""

    error_class = "deregistration_not_authenticated"

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(
            message,
            reason="No valid authentication session found.",
            repair_suggestions=["Run 'keyhole login' first."],
        )


class DeregistrationOwnershipMismatchError(DeregistrationError):
    """Acting identity does not match the target registration — §19."""

    error_class = "deregistration_ownership_mismatch"

    def __init__(
        self,
        acting_id: str = "",
        target_id: str = "",
    ) -> None:
        msg = "Ownership mismatch"
        if acting_id and target_id:
            msg = f"Authenticated as {acting_id} but requesting deletion of {target_id}"
        super().__init__(
            msg,
            reason="The acting identity does not match the target registration.",
            repair_suggestions=[
                "Log in as the account owner, then retry.",
                "Verify the --registration-id value is correct.",
            ],
        )


class DeregistrationSurfaceUnavailableError(DeregistrationError):
    """Boundary does not declare deletion support — §19."""

    error_class = "deregistration_surface_unavailable"

    def __init__(self, message: str = "Deletion surface unavailable") -> None:
        super().__init__(
            message,
            reason="The live boundary does not currently declare account deletion support.",
            repair_suggestions=[
                "The live boundary does not currently declare account deletion support.",
                "Check 'keyhole surfaces' to inspect available boundary features.",
                "Contact platform support if you believe this is an error.",
            ],
        )


class DeregistrationPolicyBlockedError(DeregistrationError):
    """Server policy prevents deletion — §19."""

    error_class = "deregistration_policy_blocked"

    def __init__(
        self,
        message: str = "Deletion blocked by server policy",
        *,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            reason=reason or "Deletion is blocked by server policy.",
            repair_suggestions=[
                "Deletion is blocked by server policy; generate a support bundle or contact support/admin.",
                "Try: keyhole support-bundle <run-id>",
            ],
        )


class DeregistrationAlreadyDeletedError(DeregistrationError):
    """Target identity is already deleted — §19."""

    error_class = "deregistration_already_deleted"

    def __init__(self, message: str = "Account already deleted") -> None:
        super().__init__(
            message,
            reason="The target identity has already been removed.",
            repair_suggestions=[
                "Inspect the prior deletion outcome instead of retrying a new delete.",
            ],
        )


class DeregistrationNetworkError(DeregistrationError):
    """Network failure during deregistration — §19."""

    error_class = "deregistration_network_error"

    def __init__(self, message: str = "Network connectivity failure") -> None:
        super().__init__(
            message,
            reason="Could not reach the MCP boundary.",
            repair_suggestions=[
                "Check network connectivity.",
                "Verify the MCP server URL is correct.",
                "Try again in a few moments.",
            ],
        )
