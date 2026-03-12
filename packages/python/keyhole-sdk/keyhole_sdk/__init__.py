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
