"""Capability-driven auth flow selection for SDK-CLIENT-25.

Implements §5.1 "Flow Selection" and §7.1 "Capability Discovery":

  Fetch /mcp/v1/capabilities
    ↓
  If device_authorization supported: use device authorization
  Else if authorization_code_pkce supported: use PKCE fallback
  Else: fail with clear unsupported-auth error

The client never selects custom magic-link queue flows.
The client never decides authority — it only chooses transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from keyhole_sdk.discovery.models import AuthPosture, CapabilitiesResult


class AuthFlowName(str, Enum):
    """Canonical OAuth flow names advertised by SDK-SERVER-25."""

    DEVICE_AUTHORIZATION = "device_authorization"
    AUTHORIZATION_CODE_PKCE = "authorization_code_pkce"


# Flows we will never select — the server contract forbids them.
_FORBIDDEN_FLOWS = frozenset({
    "custom_magic_link_queue",
    "magic_link_queue",
    "mcp_magic_link",
    "password",
    "ropc",
})


class UnsupportedAuthFlowError(Exception):
    """Raised when no supported interactive auth flow is advertised."""

    def __init__(
        self,
        message: str,
        *,
        advertised: Optional[List[str]] = None,
        repair_suggestions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.advertised = list(advertised or [])
        self.repair_suggestions = list(repair_suggestions or [])


@dataclass(frozen=True)
class AuthFlowDecision:
    """Result of capability-driven flow selection.

    Attributes:
        flow: The selected canonical OAuth flow.
        reason: Why this flow was selected (for diagnostics).
        considered: All advertised flows the client looked at.
        preferred: Server-advertised preferred interactive flow.
    """

    flow: AuthFlowName
    reason: str
    considered: List[str] = field(default_factory=list)
    preferred: str = ""

    def to_safe_dict(self) -> dict:
        """Return a redaction-safe representation for diagnostics."""
        return {
            "flow": self.flow.value,
            "reason": self.reason,
            "considered": list(self.considered),
            "preferred": self.preferred,
        }


def select_auth_flow(
    capabilities: CapabilitiesResult,
    *,
    allow_pkce_when_unadvertised: bool = False,
) -> AuthFlowDecision:
    """Select an interactive auth flow from server capabilities.

    Args:
        capabilities: Result of ``GET /mcp/v1/capabilities``.
        allow_pkce_when_unadvertised: If the boundary returns no
            ``supported_flows`` at all, allow falling back to PKCE.
            §7.1: "If capabilities are unavailable, client may fallback
            to existing PKCE only if configured to do so."

    Returns:
        :class:`AuthFlowDecision` indicating the chosen flow.

    Raises:
        UnsupportedAuthFlowError: When no permitted flow is supported.
    """
    auth: AuthPosture = capabilities.auth
    advertised = list(auth.supported_flows or [])
    preferred = (auth.preferred_interactive_flow or "").strip()

    # Reject forbidden flows even if the server lists them — defense in depth.
    safe_flows = [f for f in advertised if f not in _FORBIDDEN_FLOWS]

    # Honor server preference when it points at a supported, permitted flow.
    if (
        preferred == AuthFlowName.DEVICE_AUTHORIZATION.value
        and AuthFlowName.DEVICE_AUTHORIZATION.value in safe_flows
    ):
        return AuthFlowDecision(
            flow=AuthFlowName.DEVICE_AUTHORIZATION,
            reason="server_preferred_device_authorization",
            considered=advertised,
            preferred=preferred,
        )

    if AuthFlowName.DEVICE_AUTHORIZATION.value in safe_flows:
        return AuthFlowDecision(
            flow=AuthFlowName.DEVICE_AUTHORIZATION,
            reason="device_authorization_advertised",
            considered=advertised,
            preferred=preferred,
        )

    if AuthFlowName.AUTHORIZATION_CODE_PKCE.value in safe_flows:
        return AuthFlowDecision(
            flow=AuthFlowName.AUTHORIZATION_CODE_PKCE,
            reason="pkce_fallback_advertised",
            considered=advertised,
            preferred=preferred,
        )

    if not advertised and allow_pkce_when_unadvertised:
        return AuthFlowDecision(
            flow=AuthFlowName.AUTHORIZATION_CODE_PKCE,
            reason="pkce_fallback_capabilities_unavailable",
            considered=advertised,
            preferred=preferred,
        )

    raise UnsupportedAuthFlowError(
        "No supported interactive auth flow is advertised by the boundary.",
        advertised=advertised,
        repair_suggestions=[
            "Re-discover capabilities: GET /mcp/v1/capabilities",
            "Ensure the server advertises 'device_authorization' or "
            "'authorization_code_pkce' in auth.supported_flows.",
            "Contact your Keyhole administrator if the boundary is "
            "configured for an unsupported auth model.",
        ],
    )
