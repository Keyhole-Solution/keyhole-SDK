"""Onboarding errors — deterministic failure classes.

Every failure produces an error_class slug, reason, and repair
guidance.  Pattern mirrors ``auth_bootstrap.errors``.
"""

from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.exceptions import KeyholeSDKError


class OnboardingError(KeyholeSDKError):
    """Base error for onboarding failures."""

    error_class: str = "onboarding_error"

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


class OnboardingNetworkError(OnboardingError):
    """Network failure during onboarding API call."""

    error_class = "onboarding_network_error"

    def __init__(self, message: str = "Network connectivity failure") -> None:
        super().__init__(
            message,
            reason="Could not reach the onboarding endpoint.",
            repair_suggestions=[
                "Check network connectivity.",
                "Verify the MCP server URL is correct.",
                "Try again in a few moments.",
            ],
        )


class RegistrationRejectedError(OnboardingError):
    """Server rejected the registration request."""

    error_class = "registration_rejected"

    def __init__(
        self,
        message: str = "Registration rejected by server",
        *,
        reason: Optional[str] = None,
        repair_suggestions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            message,
            reason=reason or "The registration request was rejected.",
            repair_suggestions=repair_suggestions or [
                "Check registration fields for correctness.",
                "Verify the target realm is correct.",
                "Try: keyhole register --help",
            ],
        )


class DuplicateRegistrationError(OnboardingError):
    """Username or email is already registered."""

    error_class = "duplicate_registration"

    def __init__(self, message: str = "Identity already registered") -> None:
        super().__init__(
            message,
            reason="An identity with this username or email already exists.",
            repair_suggestions=[
                "Use a different username or email.",
                "If this is your account, proceed to: keyhole login",
                "Check registration status: keyhole registration-status --registration-id <id>",
            ],
        )


class MissingClassificationError(OnboardingError):
    """Required classification fields missing for dev/test registration."""

    error_class = "missing_classification"

    def __init__(
        self,
        missing_fields: List[str],
    ) -> None:
        detail = f"Missing required classification fields for kh-dev: {', '.join(missing_fields)}"
        super().__init__(
            detail,
            reason="Dev/test onboarding requires explicit origin and purpose.",
            repair_suggestions=[
                f"Add --{f} to your registration command." for f in missing_fields
            ] + [
                "Example: keyhole register --realm kh-dev --origin smoke --purpose sdk_onboarding",
            ],
        )
        self.missing_fields = missing_fields


class VerificationFailedError(OnboardingError):
    """Verification attempt was rejected."""

    error_class = "verification_failed"

    def __init__(
        self,
        message: str = "Verification failed",
        *,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            reason=reason or "The verification code or token was rejected.",
            repair_suggestions=[
                "Check the verification code for typos.",
                "Request a new verification: keyhole resend-verification --registration-id <id>",
                "Complete verification promptly — codes expire.",
            ],
        )


class VerificationExpiredError(OnboardingError):
    """Verification code or token has expired."""

    error_class = "verification_expired"

    def __init__(self, message: str = "Verification expired") -> None:
        super().__init__(
            message,
            reason="Verification token expired before completion.",
            repair_suggestions=[
                "Request a new verification: keyhole resend-verification --registration-id <id>",
                "Complete verification promptly after receiving the new code.",
            ],
        )
