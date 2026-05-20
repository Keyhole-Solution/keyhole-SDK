"""Authentication bootstrap models — typed data objects for auth flows.

All models are Pydantic-based for strict validation and serialization.
Secrets are never exposed in repr, str, or default serialization.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from keyhole_sdk.auth_bootstrap.actor_envelope import ActorEnvelope
from keyhole_sdk.config import DEFAULT_REALM


class AuthFlowType(str, Enum):
    """Supported authentication flow types."""

    PKCE = "pkce"
    DEVICE = "device"
    PASSWORD = "password"  # Resource Owner Password Credentials (ROPC); dev/test only
    PASSWORDLESS = "passwordless"  # Email code-based login (no password required)


class AuthMode(str, Enum):
    """Participation mode — shadow (noncanonical) or real (governed)."""

    SHADOW = "shadow"
    REAL = "real"


class PKCEChallenge(BaseModel):
    """PKCE challenge parameters for browser-based auth."""

    code_verifier: str = Field(repr=False)
    code_challenge: str
    code_challenge_method: str = "S256"
    state: str
    authorization_url: str
    redirect_uri: str = f"http://localhost:{os.environ.get('KEYHOLE_PKCE_PORT', '9876')}/callback"


class DeviceCodeResponse(BaseModel):
    """Device authorization response from the auth server."""

    device_code: str = Field(repr=False)
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str] = None
    expires_in: int = 600
    interval: int = 5


class TokenResponse(BaseModel):
    """Token response from auth server — secrets masked in repr."""

    access_token: str = Field(repr=False)
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = Field(default=None, repr=False)
    scope: Optional[str] = None
    id_token: Optional[str] = Field(default=None, repr=False)


class AuthSession(BaseModel):
    """Persisted authentication session — the local credential store entry.

    Secrets are never exposed in repr or default str output.
    """

    access_token: str = Field(repr=False)
    token_type: str = "Bearer"
    refresh_token: Optional[str] = Field(default=None, repr=False)
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    flow_type: AuthFlowType
    mode: AuthMode = AuthMode.REAL
    realm: str = DEFAULT_REALM
    auth_server_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if the session token appears expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def token_fingerprint(self) -> str:
        """Return a safe fingerprint of the token (first 8 chars of SHA-256)."""
        return hashlib.sha256(self.access_token.encode()).hexdigest()[:8]

    def safe_summary(self) -> Dict[str, Any]:
        """Return a dict safe for logging/proof — no secrets."""
        return {
            "token_fingerprint": self.token_fingerprint,
            "token_type": self.token_type,
            "flow_type": self.flow_type.value,
            "mode": self.mode.value,
            "realm": self.realm,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_verified_at": (
                self.last_verified_at.isoformat() if self.last_verified_at else None
            ),
            "has_refresh_token": self.refresh_token is not None,
        }


# Required fields for governed identity — the server must return these.
_REQUIRED_IDENTITY_FIELDS = ("user_id", "mode")


class WhoamiResponse(BaseModel):
    """Identity context returned by the /mcp/v1/whoami endpoint.

    Identity is server-issued only. The client must never construct,
    infer, or locally reconstruct any of these fields.

    SDK-CLIENT-29: surfaces the sanitized ``actor_envelope`` resolved
    by SDK-SERVER-29.  The envelope is the authoritative actor truth;
    the older flat ``user_id``/``tenant_id`` fields are kept for
    backward compatibility with pre-SDK-SERVER-29 servers.
    """

    model_config = ConfigDict(extra="allow")

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    cohort_id: Optional[str] = None
    worker_id: Optional[str] = None
    workspace_id: Optional[str] = None
    plan: Optional[str] = None
    mode: AuthMode = AuthMode.REAL
    display_name: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    limits: Optional[Dict[str, Any]] = None
    actor_envelope: Optional[ActorEnvelope] = None

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, v: Any) -> AuthMode:
        if isinstance(v, str):
            return AuthMode(v.lower())
        return v

    def validate_required_identity(self) -> List[str]:
        """Validate that all required governed identity fields are present.

        Returns a list of missing field names. Empty list means valid.
        """
        missing = []
        for field_name in _REQUIRED_IDENTITY_FIELDS:
            value = getattr(self, field_name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field_name)
        return missing


class LoginResult(BaseModel):
    """Result of a complete login flow — returned to the CLI layer.

    Success requires:
      - usable token/session received
      - /whoami returned valid governed identity
      - credentials persisted after identity confirmation

    Mode, identity, and all governed fields come from the server only.
    """

    success: bool
    flow_type: Optional[AuthFlowType] = None
    mode: Optional[AuthMode] = None
    whoami: Optional[WhoamiResponse] = None
    correlation_id: Optional[str] = None
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    repair_suggestions: List[str] = Field(default_factory=list)
    credential_persisted: bool = False
    verification_passed: bool = False
    identity_source: Optional[str] = None

    def safe_summary(self) -> Dict[str, Any]:
        """Return a summary safe for proof artifacts."""
        return {
            "success": self.success,
            "flow_type": self.flow_type.value if self.flow_type else None,
            "mode": self.mode.value if self.mode else None,
            "correlation_id": self.correlation_id,
            "credential_persisted": self.credential_persisted,
            "verification_passed": self.verification_passed,
            "identity_source": self.identity_source,
            "error_class": self.error_class,
            "has_whoami": self.whoami is not None,
        }
