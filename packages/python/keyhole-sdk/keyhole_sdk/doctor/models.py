"""SDK-CLIENT-01-C — Doctor discovery models for host identity reconciliation.

Provides typed models for:
  - Host inventory records (§10.1)
  - Doctor report aggregation (§10.2)
  - Host diagnosis classification (§13)
  - Staleness and summary status (§9.1)
"""
from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class HostType(str, enum.Enum):
    """Type of MCP-capable host environment (§8.1)."""

    IDE_MCP_CLIENT = "ide_mcp_client"
    SDK_RUNTIME = "sdk_runtime"
    UNKNOWN = "unknown"


class StalenessState(str, enum.Enum):
    """Staleness classification for a host connection (§10.1)."""

    FRESH = "fresh"
    STALE_CONFIRMED = "stale_confirmed"
    UNKNOWN = "unknown"


class HostDiagnosis(str, enum.Enum):
    """Diagnosis classification for a discovered host (§9.1, §13)."""

    ALIGNED = "aligned"
    SPLIT_IDENTITY = "split_identity"
    STALE_CONNECTION = "stale_connection"
    UNSUPPORTED_HOST = "unsupported_host"
    SURFACE_UNAVAILABLE = "surface_unavailable"
    AMBIGUOUS_CONNECTION = "ambiguous_connection"
    NOT_DETECTED = "not_detected"


class DoctorSummaryStatus(str, enum.Enum):
    """Summary status for the overall doctor report (§10.2)."""

    OK = "ok"
    ATTENTION_REQUIRED = "attention_required"
    DEGRADED = "degraded"


class RecommendedAction(str, enum.Enum):
    """Concrete repair actions a builder can take (§16)."""

    REBIND = "rebind"
    INVALIDATE_RECONNECT = "invalidate_reconnect"
    KEEP_AS_IS = "keep_as_is"
    UPGRADE_SERVER = "upgrade_server"
    USE_GENERIC_WHOAMI = "use_generic_whoami"
    INSTALL_HOST_ENTRY = "install_host_entry"
    REFRESH_HOST = "refresh_host"
    RERUN_DOCTOR = "rerun_doctor"


# ── Host Record ──────────────────────────────────────────


class DoctorHostRecord(BaseModel):
    """Structured record for a single discovered host (§10.1)."""

    host_id: str
    host_type: HostType = HostType.UNKNOWN
    display_name: str = ""
    detected: bool = False
    config_detected: bool = False
    keyhole_server_entry_detected: bool = False
    server_url: str = ""
    local_auth_hints_present: bool = False
    connection_visible_from_server: bool = False
    connection_id: str = ""
    server_principal_user_id: str = ""
    server_principal_label: str = ""
    staleness_state: StalenessState = StalenessState.UNKNOWN
    supports_rebind: bool = False
    supports_invalidate: bool = False
    diagnosis: HostDiagnosis = HostDiagnosis.NOT_DETECTED

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for JSON output and proof artifacts."""
        return {
            "host_id": self.host_id,
            "host_type": self.host_type.value,
            "display_name": self.display_name,
            "detected": self.detected,
            "config_detected": self.config_detected,
            "keyhole_server_entry_detected": self.keyhole_server_entry_detected,
            "server_url": self.server_url,
            "local_auth_hints_present": self.local_auth_hints_present,
            "connection_visible_from_server": self.connection_visible_from_server,
            "connection_id": self.connection_id,
            "server_principal_user_id": self.server_principal_user_id,
            "server_principal_label": self.server_principal_label,
            "staleness_state": self.staleness_state.value,
            "supports_rebind": self.supports_rebind,
            "supports_invalidate": self.supports_invalidate,
            "diagnosis": self.diagnosis.value,
        }


# ── Host Report Entry ────────────────────────────────────


class DoctorHostEntry(BaseModel):
    """Per-host summary inside a DoctorReport (§10.2)."""

    host_id: str
    diagnosis: HostDiagnosis = HostDiagnosis.NOT_DETECTED
    current_connection_principal: str = ""
    recommended_actions: List[RecommendedAction] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host_id": self.host_id,
            "diagnosis": self.diagnosis.value,
            "current_connection_principal": self.current_connection_principal,
            "recommended_actions": [a.value for a in self.recommended_actions],
        }


# ── Doctor Report ────────────────────────────────────────


class DoctorReport(BaseModel):
    """Aggregated doctor report across all hosts (§10.2)."""

    cli_active_profile: str = ""
    cli_user_id: str = ""
    hosts: List[DoctorHostEntry] = Field(default_factory=list)
    host_records: List[DoctorHostRecord] = Field(default_factory=list)
    summary_status: DoctorSummaryStatus = DoctorSummaryStatus.OK
    negotiation_available: bool = False
    connection_surfaces_available: bool = False
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cli_active_profile": self.cli_active_profile,
            "cli_user_id": self.cli_user_id,
            "hosts": [h.to_dict() for h in self.hosts],
            "host_records": [r.to_dict() for r in self.host_records],
            "summary_status": self.summary_status.value,
            "negotiation_available": self.negotiation_available,
            "connection_surfaces_available": self.connection_surfaces_available,
            "correlation_id": self.correlation_id,
        }

    def has_split_identity(self) -> bool:
        """Return True if any host has split identity."""
        return any(
            h.diagnosis == HostDiagnosis.SPLIT_IDENTITY for h in self.hosts
        )

    def has_attention_required(self) -> bool:
        """Return True if any host needs attention."""
        return self.summary_status != DoctorSummaryStatus.OK


# ── Repair Guidance ──────────────────────────────────────


class RepairGuidance(BaseModel):
    """Concrete repair guidance for a host diagnosis (§16)."""

    host_id: str
    diagnosis: HostDiagnosis
    actions: List[RecommendedAction] = Field(default_factory=list)
    descriptions: List[str] = Field(default_factory=list)
    commands: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host_id": self.host_id,
            "diagnosis": self.diagnosis.value,
            "actions": [a.value for a in self.actions],
            "descriptions": self.descriptions,
            "commands": self.commands,
        }
