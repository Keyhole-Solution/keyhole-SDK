"""Browser OIDC compatibility models — typed data objects.

Implements §13 of SDK-CLIENT-01-F: Validation Model.

All models are Pydantic-based for strict validation and serialization.
No secrets ever appear in these models — they are diagnostic artifacts only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BrowserCheckVerdict(str, Enum):
    """Final compatibility verdict from a browser-check run."""

    COMPATIBLE = "compatible"
    BLOCKED = "blocked"
    MISCONFIGURED = "misconfigured"
    UNSUPPORTED_DETOUR_DETECTED = "unsupported_detour_detected"


class BrowserFailureClass(str, Enum):
    """Classification for detected browser-auth failure modes."""

    PASSWORDLESS_BROWSER_NOT_SUPPORTED = "passwordless_browser_not_supported"
    OIDC_DISCOVERY_UNAVAILABLE = "oidc_discovery_unavailable"
    REDIRECT_URI_MISMATCH = "redirect_uri_mismatch"
    UNSUPPORTED_DETOUR_DETECTED = "unsupported_detour_detected"
    BROWSER_AUTH_TIMEOUT = "browser_auth_timeout"
    LOOPBACK_CALLBACK_NOT_COMPLETED = "loopback_callback_not_completed"


class RedirectPosture(str, Enum):
    """Posture of the redirect URI provided or inferred."""

    LOOPBACK = "loopback"       # http://127.0.0.1:<port>/ or http://localhost:<port>/
    CUSTOM_SCHEME = "custom_scheme"
    MISMATCH = "mismatch"
    NOT_PROVIDED = "not_provided"
    INVALID = "invalid"


class PkcePosture(str, Enum):
    """PKCE support posture from discovery metadata."""

    SUPPORTED = "supported"
    NOT_ADVERTISED = "not_advertised"
    UNKNOWN = "unknown"


class PasswordlessBrowserPosture(str, Enum):
    """Server-side passwordless browser continuation support posture."""

    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    UNKNOWN = "unknown"


class DirectMcpPosture(str, Enum):
    """Whether the auth endpoint config points directly at Keyhole or via a detour."""

    DIRECT = "direct"
    DETOUR = "detour"
    UNKNOWN = "unknown"


class RepairItem(BaseModel):
    """A single actionable repair step."""

    step: int
    instruction: str
    failure_class: Optional[BrowserFailureClass] = None


class BrowserCompatibilityReport(BaseModel):
    """Full compatibility report from a browser-check run.

    §13.1 BrowserCompatibilityReport shape.
    """

    realm: str
    client_id: str
    issuer: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    redirect_uri: Optional[str] = None
    pkce_posture: PkcePosture = PkcePosture.UNKNOWN
    passwordless_browser_posture: PasswordlessBrowserPosture = PasswordlessBrowserPosture.UNKNOWN
    direct_mcp_posture: DirectMcpPosture = DirectMcpPosture.UNKNOWN
    unsupported_detour_detected: bool = False
    discovery_reachable: bool = False
    redirect_posture: RedirectPosture = RedirectPosture.NOT_PROVIDED
    verdict: BrowserCheckVerdict = BrowserCheckVerdict.BLOCKED
    failure_classes: List[BrowserFailureClass] = Field(default_factory=list)
    repair: List[RepairItem] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BrowserSupportBundleIndex(BaseModel):
    """Index / manifest for a generated support bundle.

    §13.2 BrowserSupportBundleIndex shape.
    """

    bundle_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    realm: str
    client_id: str
    redirect_uri: Optional[str] = None
    verdict: BrowserCheckVerdict
    classification: Optional[BrowserFailureClass] = None
    artifacts: List[str] = Field(default_factory=list)
    bundle_path: Optional[str] = None
