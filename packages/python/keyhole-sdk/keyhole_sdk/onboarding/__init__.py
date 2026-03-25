"""DEV-SDK-00 — Client-side identity creation and verification.

Provides the SDK layer for builder onboarding: registration,
verification, status inspection, and proof bundle generation.
"""

from keyhole_sdk.onboarding.models import (
    OnboardingRealm,
    OnboardingState,
    RegistrationRequest,
    RegistrationResponse,
    VerificationRequest,
    VerificationResponse,
    RegistrationStatusResponse,
    OnboardingResult,
)
from keyhole_sdk.onboarding.errors import (
    OnboardingError,
    RegistrationRejectedError,
    VerificationFailedError,
    VerificationExpiredError,
    DuplicateRegistrationError,
    MissingClassificationError,
    OnboardingNetworkError,
)
from keyhole_sdk.onboarding.client import OnboardingClient
from keyhole_sdk.onboarding.proof import OnboardingProofBundle

__all__ = [
    "OnboardingRealm",
    "OnboardingState",
    "RegistrationRequest",
    "RegistrationResponse",
    "VerificationRequest",
    "VerificationResponse",
    "RegistrationStatusResponse",
    "OnboardingResult",
    "OnboardingError",
    "RegistrationRejectedError",
    "VerificationFailedError",
    "VerificationExpiredError",
    "DuplicateRegistrationError",
    "MissingClassificationError",
    "OnboardingNetworkError",
    "OnboardingClient",
    "OnboardingProofBundle",
]
