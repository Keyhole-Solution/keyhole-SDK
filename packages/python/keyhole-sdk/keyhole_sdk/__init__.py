"""Keyhole SDK — canonical public Python client surface.

CE-V5-S41-05: SDK Surface Contract.

Public entry points per §11:
  KeyholeClient      — synchronous client
  AsyncKeyholeClient — asynchronous client (placeholder, sync wrapper)
  KeyholeConfig      — narrow configuration object
  KeyholeError       — base exception
  AuthProvider       — pluggable auth base
"""

__version__ = "0.3.0"

# ── Core client entry points ────────────────────────────
from keyhole_sdk.client import KeyholeClient, RuntimeBridgeClient  # noqa: E402

# ── Configuration ────────────────────────────────────────
from keyhole_sdk.config import KeyholeConfig  # noqa: E402

# ── Authentication ───────────────────────────────────────
from keyhole_sdk.auth import (  # noqa: E402
    AuthProvider,
    BearerTokenProvider,
    CallbackTokenProvider,
    EnvironmentTokenProvider,
)

# ── Models ───────────────────────────────────────────────
from keyhole_sdk import models  # noqa: E402
from keyhole_sdk.models import (  # noqa: E402
    CompatibilityResult,
    CompatibilityStatus,
    PublicError,
    RealizationReceipt,
    RealizationRequest,
    RuntimeHealth,
    RuntimeIdentity,
    RuntimeState,
)

# ── Discovery ─────────────────────────────────────────────
from keyhole_sdk.discovery import (  # noqa: E402
    CapabilitiesCache,
    CapabilitiesClient,
    CapabilitiesResult,
)

# ── Context Retrieval ─────────────────────────────────────
from keyhole_sdk.context import (  # noqa: E402
    ContextClient,
    ContextSnapshot,
)

# ── Dispatch Safety ───────────────────────────────────────
from keyhole_sdk.dispatch import (  # noqa: E402
    DispatchPreflight,
    RunTypeValidator,
    SchemaHelper,
)

# ── Read-Only Smoke Path ──────────────────────────────────
from keyhole_sdk.smoke import (  # noqa: E402
    ReadOnlySmokeRunner,
    SmokeResult,
)

# ── Proof-Ready Scaffolding (CE-V5-S42-08) ────────────────
from keyhole_sdk.proof import (  # noqa: E402
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
    VerificationRunner,
)

# ── Recursive Demo Readiness (CE-V5-S42-09) ───────────────
from keyhole_sdk.demo import (  # noqa: E402
    DemoFlowRunner,
    DemoResult,
)

# ── Onboarding (SDK-CLIENT-00) ──────────────────────────────────
from keyhole_sdk.onboarding import (  # noqa: E402
    OnboardingClient,
    OnboardingProofBundle,
    OnboardingRealm,
    OnboardingState,
    RegistrationRequest,
    RegistrationResponse,
    VerificationRequest,
    VerificationResponse,
    RegistrationStatusResponse,
    OnboardingResult,
    OnboardingError,
    RegistrationRejectedError,
    VerificationFailedError,
    VerificationExpiredError,
    DuplicateRegistrationError,
    MissingClassificationError,
    OnboardingNetworkError,
)

# ── Governance Proof Protocol (RG-01) ─────────────────────
from keyhole_sdk.governance import (  # noqa: E402
    GovernancePhase,
    GovernanceProofResult,
    GovernanceProofRunner,
    GovernanceTraceBuilder,
)

# ── Exceptions ───────────────────────────────────────────
from keyhole_sdk.exceptions import (  # noqa: E402
    AuthenticationError,
    CompatibilityError,
    ContractIncompatibleError,
    KeyholeSDKError,
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
    ValidationError as SDKValidationError,
)

# Backward-compat alias
KeyholeError = KeyholeSDKError

__all__ = [
    # Core clients
    "KeyholeClient",
    "RuntimeBridgeClient",
    # Configuration
    "KeyholeConfig",
    # Auth
    "AuthProvider",
    "BearerTokenProvider",
    "CallbackTokenProvider",
    "EnvironmentTokenProvider",
    # Models
    "models",
    "RuntimeIdentity",
    "RuntimeHealth",
    "RuntimeState",
    "RealizationRequest",
    "RealizationReceipt",
    "CompatibilityResult",
    "CompatibilityStatus",
    "PublicError",
    # Discovery
    "CapabilitiesClient",
    "CapabilitiesResult",
    "CapabilitiesCache",
    # Context Retrieval
    "ContextClient",
    "ContextSnapshot",
    # Dispatch Safety
    "DispatchPreflight",
    "RunTypeValidator",
    "SchemaHelper",
    # Read-Only Smoke Path
    "ReadOnlySmokeRunner",
    "SmokeResult",
    # Proof-Ready Scaffolding (CE-V5-S42-08)
    "ParticipantContractPlaceholder",
    "ProofBundlePlaceholder",
    "SupportStatus",
    "VerificationOutput",
    "VerificationRunner",
    # Recursive Demo Readiness (CE-V5-S42-09)
    "DemoFlowRunner",
    "DemoResult",
    # Onboarding (SDK-CLIENT-00)
    "OnboardingClient",
    "OnboardingProofBundle",
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
    # Governance Proof Protocol (RG-01)
    "GovernancePhase",
    "GovernanceProofResult",
    "GovernanceProofRunner",
    "GovernanceTraceBuilder",
    # Exceptions
    "KeyholeSDKError",
    "KeyholeError",
    "TransportError",
    "RuntimeUnavailableError",
    "SchemaError",
    "CompatibilityError",
    "PublicEndpointError",
    "AuthenticationError",
    "ContractIncompatibleError",
    "SDKValidationError",
]
