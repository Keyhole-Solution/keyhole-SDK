"""Onboarding data models — registration, verification, and status.

All models follow the same conventions as ``auth_bootstrap.models``:
secrets are ``Field(repr=False)``, ``safe_summary()`` returns proof-safe
dicts, and enums are string-based for deterministic serialization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class OnboardingRealm(str, Enum):
    """Target realm for identity creation."""

    KH_PROD = "kh-prod"
    KH_DEV = "kh-dev"
    KEYHOLE_MCP = "keyhole-mcp"


class OnboardingState(str, Enum):
    """Lifecycle state of an onboarding identity."""

    PENDING_VERIFICATION = "pending_verification"
    # Server-emitted lifecycle state strings
    REGISTERED_PENDING_VERIFICATION = "registered_pending_verification"
    VERIFIED = "verified"
    VERIFIED_ACTIVE = "verified_active"
    ACTIVATION_READY = "activation_ready"
    ACTIVE = "active"
    FAILED = "failed"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"


# ── Requests ────────────────────────────────────────────────


class RegistrationRequest(BaseModel):
    """Client-shaped registration request."""

    email: str
    username: str
    display_name: str
    realm: OnboardingRealm = OnboardingRealm.KH_DEV
    origin: Optional[str] = None
    purpose: Optional[str] = None
    tenant: Optional[str] = None
    org: Optional[str] = None

    def validate_classification(self) -> List[str]:
        """Return missing classification fields for kh-dev onboarding."""
        if self.realm != OnboardingRealm.KH_DEV:
            return []
        missing: List[str] = []
        if not self.origin:
            missing.append("origin")
        if not self.purpose:
            missing.append("purpose")
        return missing


class VerificationRequest(BaseModel):
    """Client-shaped verification completion request."""

    registration_id: str
    code: Optional[str] = None
    token: Optional[str] = Field(default=None, repr=False)


# ── Responses ───────────────────────────────────────────────


class RegistrationResponse(BaseModel):
    """Server response to a registration request."""

    registration_id: str
    state: OnboardingState
    realm: OnboardingRealm
    origin: Optional[str] = None
    purpose: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    verification_hint: Optional[str] = None
    next_step: Optional[str] = None
    message: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_server_fields(cls, v: Any) -> Any:
        """Map server-side field names to client model fields."""
        if isinstance(v, dict):
            v = dict(v)
            if "user_id" in v and "registration_id" not in v:
                v["registration_id"] = v["user_id"]
            if "lifecycle_state" in v and "state" not in v:
                v["state"] = v["lifecycle_state"]
        return v

    def safe_summary(self) -> Dict[str, Any]:
        """Return dict safe for proof / logging."""
        return {
            "registration_id": self.registration_id,
            "state": self.state.value,
            "realm": self.realm.value,
            "origin": self.origin,
            "purpose": self.purpose,
            "username": self.username,
            "verification_hint": self.verification_hint,
            "next_step": self.next_step,
        }


class VerificationResponse(BaseModel):
    """Server response to a verification completion request."""

    registration_id: str
    state: OnboardingState
    user_id: Optional[str] = None
    username: Optional[str] = None
    realm: Optional[str] = None
    message: Optional[str] = None
    next_step: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_server_fields(cls, v: Any) -> Any:
        if isinstance(v, dict):
            v = dict(v)
            if "user_id" in v and "registration_id" not in v:
                v["registration_id"] = v["user_id"]
            if "lifecycle_state" in v and "state" not in v:
                v["state"] = v["lifecycle_state"]
        return v

    def safe_summary(self) -> Dict[str, Any]:
        """Return dict safe for proof / logging."""
        return {
            "registration_id": self.registration_id,
            "state": self.state.value,
            "user_id": self.user_id,
            "username": self.username,
            "realm": self.realm,
            "next_step": self.next_step,
        }


class RegistrationStatusResponse(BaseModel):
    """Server response to a status inspection request."""

    registration_id: str
    state: OnboardingState
    realm: Optional[str] = None
    origin: Optional[str] = None
    purpose: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None
    next_step: Optional[str] = None
    message: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_server_fields(cls, v: Any) -> Any:
        if isinstance(v, dict):
            v = dict(v)
            if "user_id" in v and "registration_id" not in v:
                v["registration_id"] = v["user_id"]
            if "lifecycle_state" in v and "state" not in v:
                v["state"] = v["lifecycle_state"]
            # Map next_step_hint → next_step
            if "next_step_hint" in v and "next_step" not in v:
                v["next_step"] = v["next_step_hint"]
        return v

    def safe_summary(self) -> Dict[str, Any]:
        """Return dict safe for proof / logging."""
        return {
            "registration_id": self.registration_id,
            "state": self.state.value,
            "realm": self.realm,
            "origin": self.origin,
            "purpose": self.purpose,
            "username": self.username,
            "user_id": self.user_id,
            "next_step": self.next_step,
        }


# ── Aggregate result ────────────────────────────────────────


class OnboardingResult(BaseModel):
    """Complete client-side onboarding result across all phases."""

    success: bool
    state: OnboardingState = OnboardingState.PENDING_VERIFICATION
    registration_id: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    realm: Optional[str] = None
    origin: Optional[str] = None
    purpose: Optional[str] = None
    correlation_id: Optional[str] = None
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    repair_suggestions: List[str] = Field(default_factory=list)
    next_step: Optional[str] = None

    def safe_summary(self) -> Dict[str, Any]:
        """Return dict safe for proof / logging."""
        d: Dict[str, Any] = {
            "success": self.success,
            "state": self.state.value,
            "registration_id": self.registration_id,
            "correlation_id": self.correlation_id,
            "realm": self.realm,
            "origin": self.origin,
            "purpose": self.purpose,
        }
        if self.user_id:
            d["user_id"] = self.user_id
        if self.error_class:
            d["error_class"] = self.error_class
            d["error_message"] = self.error_message
        return d
