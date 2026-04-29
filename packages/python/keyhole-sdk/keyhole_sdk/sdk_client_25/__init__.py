"""SDK-CLIENT-25 — VS Code MCP passwordless auth client.

Implements the client-side contract from SDK-CLIENT-25:

  - capability-driven auth flow selection
  - OAuth 2.0 Device Authorization Grant (RFC 8628)
  - portable magic-link via ``verification_uri_complete``
  - bounded polling with ``slow_down`` / ``authorization_pending`` handling
  - auth attempt supersession (only one active attempt may store creds)
  - logout / re-auth state hygiene (no stale ``initialize`` hangs)
  - identity mismatch detection (server-resolved identity is canonical)
  - redaction-first local diagnostics

This package does NOT:

  - decode JWTs for authority decisions (tokens are opaque)
  - implement custom MCP magic-link queues
  - replace SDK-CLIENT-01 PKCE / passwordless flows (PKCE is preserved
    as fallback per §5.1)
"""

from keyhole_sdk.sdk_client_25.flow_selection import (
    AuthFlowDecision,
    AuthFlowName,
    UnsupportedAuthFlowError,
    select_auth_flow,
)
from keyhole_sdk.sdk_client_25.device_flow import (
    DeviceAuthorizationResponse,
    DevicePollOutcome,
    DevicePollStatus,
    DeviceAuthorizationFlow,
    DeviceAuthorizationCancelled,
    DeviceAuthorizationDenied,
    DeviceAuthorizationExpired,
    DeviceAuthorizationNetworkError,
)
from keyhole_sdk.sdk_client_25.auth_state import (
    AuthAttempt,
    AuthAttemptRegistry,
    LogoutResult,
    SignOutManager,
)
from keyhole_sdk.sdk_client_25.identity_match import (
    IdentityMatchResult,
    IdentityMismatchError,
    detect_identity_mismatch,
)
from keyhole_sdk.sdk_client_25.diagnostics import (
    DiagnosticEvent,
    DiagnosticRecorder,
    redact_text,
)

__all__ = [
    # Flow selection
    "AuthFlowName",
    "AuthFlowDecision",
    "UnsupportedAuthFlowError",
    "select_auth_flow",
    # Device authorization
    "DeviceAuthorizationFlow",
    "DeviceAuthorizationResponse",
    "DevicePollOutcome",
    "DevicePollStatus",
    "DeviceAuthorizationCancelled",
    "DeviceAuthorizationDenied",
    "DeviceAuthorizationExpired",
    "DeviceAuthorizationNetworkError",
    # Auth state
    "AuthAttempt",
    "AuthAttemptRegistry",
    "LogoutResult",
    "SignOutManager",
    # Identity match
    "IdentityMatchResult",
    "IdentityMismatchError",
    "detect_identity_mismatch",
    # Diagnostics
    "DiagnosticEvent",
    "DiagnosticRecorder",
    "redact_text",
]
