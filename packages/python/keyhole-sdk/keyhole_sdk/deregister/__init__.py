"""SDK-CLIENT-22 — Account Deregistration and Deletion UX.

Provides the SDK layer for account deletion: dispatch through
the governed run surface, proof generation, and typed errors.
"""

from keyhole_sdk.deregister.models import (
    DeregistrationOutcome,
    DeregistrationRequest,
    DeregistrationStatus,
)
from keyhole_sdk.deregister.errors import (
    DeregistrationAlreadyDeletedError,
    DeregistrationError,
    DeregistrationNetworkError,
    DeregistrationNotAuthenticatedError,
    DeregistrationOwnershipMismatchError,
    DeregistrationPolicyBlockedError,
    DeregistrationSurfaceUnavailableError,
)
from keyhole_sdk.deregister.client import DeregistrationClient
from keyhole_sdk.deregister.proof import DeregistrationProofBundle

__all__ = [
    "DeregistrationClient",
    "DeregistrationProofBundle",
    "DeregistrationOutcome",
    "DeregistrationRequest",
    "DeregistrationStatus",
    "DeregistrationAlreadyDeletedError",
    "DeregistrationError",
    "DeregistrationNetworkError",
    "DeregistrationNotAuthenticatedError",
    "DeregistrationOwnershipMismatchError",
    "DeregistrationPolicyBlockedError",
    "DeregistrationSurfaceUnavailableError",
]
