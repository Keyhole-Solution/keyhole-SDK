"""Public Python SDK surface for Keyhole-governed applications."""

__version__ = "0.4.1"

from keyhole_sdk.auth import AuthProvider, BearerTokenProvider, EnvironmentTokenProvider
from keyhole_sdk.client import KeyholeClient, RuntimeBridgeClient
from keyhole_sdk.config import KeyholeConfig
from keyhole_sdk.exceptions import (
    AuthenticationError,
    CompatibilityError,
    KeyholeSDKError,
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.models import (
    CompatibilityResult,
    CompatibilityStatus,
    GovernanceReceipt,
    RealizationReceipt,
    RealizationRequest,
    RuntimeHealth,
    RuntimeIdentity,
    RuntimeState,
)
from keyhole_sdk.validation import (
    ValidationResult,
    ValidationStatus,
    run_validation,
    validate_capability_passport,
    validate_dependencies,
    validate_governance_contract,
    validate_keyhole_yaml,
)

KeyholeError = KeyholeSDKError

__all__ = [
    "AuthProvider",
    "BearerTokenProvider",
    "EnvironmentTokenProvider",
    "KeyholeClient",
    "RuntimeBridgeClient",
    "KeyholeConfig",
    "KeyholeSDKError",
    "KeyholeError",
    "AuthenticationError",
    "CompatibilityError",
    "PublicEndpointError",
    "RuntimeUnavailableError",
    "SchemaError",
    "TransportError",
    "CompatibilityResult",
    "CompatibilityStatus",
    "GovernanceReceipt",
    "RealizationReceipt",
    "RealizationRequest",
    "RuntimeHealth",
    "RuntimeIdentity",
    "RuntimeState",
    "ValidationResult",
    "ValidationStatus",
    "run_validation",
    "validate_keyhole_yaml",
    "validate_governance_contract",
    "validate_capability_passport",
    "validate_dependencies",
]
