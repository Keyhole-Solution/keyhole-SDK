"""SDK-CLIENT-01-C — Connection identity models (§9, §10).

Typed models for connection introspection, rebind, and invalidate
flows through the governed MCP boundary.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class ConnectionAuthority(str, enum.Enum):
    """Authority model for a connection's identity binding (§8)."""

    SESSION_BOUND = "session_bound"
    TOKEN_BOUND = "token_bound"
    UNKNOWN = "unknown"


class ConnectionStaleness(str, enum.Enum):
    """Staleness state of a connection from the server's perspective."""

    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class RebindStatus(str, enum.Enum):
    """Outcome status for a connection rebind request (§9.4)."""

    ACCEPTED = "accepted"
    REBOUND = "rebound"
    DEFERRED = "deferred"
    REPLAYED = "replayed"
    REJECTED = "rejected"


class InvalidateStatus(str, enum.Enum):
    """Outcome status for a connection invalidate request (§9.5)."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ALREADY_INVALIDATED = "already_invalidated"


# ── Connection Info ──────────────────────────────────────


class ConnectionInfo(BaseModel):
    """Single connection record from the server (§9.2, §9.3)."""

    connection_id: str = ""
    host_hint: str = ""
    principal: str = ""
    user_id: str = ""
    authority: ConnectionAuthority = ConnectionAuthority.UNKNOWN
    purpose: str = ""
    origin: str = ""
    bound_at: str = ""
    staleness_state: ConnectionStaleness = ConnectionStaleness.UNKNOWN
    session_lineage_id: str = ""
    supports_rebind: bool = False
    supports_invalidate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "host_hint": self.host_hint,
            "principal": self.principal,
            "user_id": self.user_id,
            "authority": self.authority.value,
            "purpose": self.purpose,
            "origin": self.origin,
            "bound_at": self.bound_at,
            "staleness_state": self.staleness_state.value,
            "session_lineage_id": self.session_lineage_id,
            "supports_rebind": self.supports_rebind,
            "supports_invalidate": self.supports_invalidate,
        }

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialisation (no secrets)."""
        return self.to_dict()


# ── Rebind Request / Outcome ─────────────────────────────


class RebindRequest(BaseModel):
    """Request to rebind a connection to a different principal (§9.4)."""

    connection_id: str = ""
    host_id: str = ""
    target_profile: str = ""
    target_user_id: str = ""
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def to_run_payload(self) -> Dict[str, Any]:
        """Wire format for POST /mcp/v1/runs/start."""
        return {
            "run_type": "connection.rebind",
            "parameters": {
                "connection_id": self.connection_id,
                "host_id": self.host_id,
                "target_profile": self.target_profile,
                "target_user_id": self.target_user_id,
            },
            "correlation_id": self.correlation_id,
        }

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "host_id": self.host_id,
            "target_profile": self.target_profile,
            "correlation_id": self.correlation_id,
        }


class RebindOutcome(BaseModel):
    """Outcome of a connection rebind request (§9.4, §13.5)."""

    status: RebindStatus = RebindStatus.REJECTED
    connection_id: str = ""
    old_principal: str = ""
    new_principal: str = ""
    run_id: str = ""
    server_message: str = ""
    repair_guidance: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "old_principal": self.old_principal,
            "new_principal": self.new_principal,
            "run_id": self.run_id,
            "server_message": self.server_message,
            "repair_guidance": self.repair_guidance,
        }

    def safe_summary(self) -> Dict[str, Any]:
        """Proof-safe summary for artifact emission."""
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "old_principal": self.old_principal,
            "new_principal": self.new_principal,
            "run_id": self.run_id,
        }


# ── Invalidate Request / Outcome ─────────────────────────


class InvalidateRequest(BaseModel):
    """Request to invalidate a stale connection (§9.5)."""

    connection_id: str = ""
    host_id: str = ""
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def to_run_payload(self) -> Dict[str, Any]:
        """Wire format for POST /mcp/v1/runs/start."""
        return {
            "run_type": "connection.invalidate",
            "parameters": {
                "connection_id": self.connection_id,
                "host_id": self.host_id,
            },
            "correlation_id": self.correlation_id,
        }

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "host_id": self.host_id,
            "correlation_id": self.correlation_id,
        }


class InvalidateOutcome(BaseModel):
    """Outcome of a connection invalidate request (§9.5, §13.6)."""

    status: InvalidateStatus = InvalidateStatus.REJECTED
    connection_id: str = ""
    reconnect_required: bool = True
    run_id: str = ""
    server_message: str = ""
    repair_guidance: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "reconnect_required": self.reconnect_required,
            "run_id": self.run_id,
            "server_message": self.server_message,
            "repair_guidance": self.repair_guidance,
        }

    def safe_summary(self) -> Dict[str, Any]:
        """Proof-safe summary for artifact emission."""
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "reconnect_required": self.reconnect_required,
            "run_id": self.run_id,
        }
