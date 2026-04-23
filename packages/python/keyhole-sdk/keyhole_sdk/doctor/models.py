"""Doctor discovery models for host identity reconciliation.

Provides typed models for:
  - Host inventory records (§10.1)
  - Doctor report aggregation (§10.2)
  - Host diagnosis classification (§13)
  - Staleness and summary status (§9.1)
  - Host principal source inspection (SDK-CLIENT-01-D §3)
  - Reconciliation verdicts (SDK-CLIENT-01-D §4)
  - Host identity attestation contract (SDK-CLIENT-23 §A)
  - Local identity coherence verdicts (SDK-CLIENT-23 §D)
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class HostType(str, enum.Enum):
    """Type of MCP-capable host environment (§8.1)."""

    IDE_MCP_CLIENT = "ide_mcp_client"
    SDK_RUNTIME = "sdk_runtime"
    UNKNOWN = "unknown"


class HostFamily(str, enum.Enum):
    """Host family for adapter dispatch (SDK-CLIENT-01-D §1)."""

    VSCODE = "vscode"
    JETBRAINS = "jetbrains"
    CLOUD_CODE = "cloud_code"
    SDK_LOCAL = "sdk_local"
    UNKNOWN = "unknown"


class HostSupportStatus(str, enum.Enum):
    """Support classification for a discovered host (SDK-CLIENT-01-D §1)."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class StalenessState(str, enum.Enum):
    """Staleness classification for a host connection (§10.1)."""

    FRESH = "fresh"
    STALE_CONFIRMED = "stale_confirmed"
    UNKNOWN = "unknown"


class HostDiagnosis(str, enum.Enum):
    """Diagnosis classification for a discovered host (§9.1, §13).

    Extended in SDK-CLIENT-01-D with additional verdict classes.
    """

    ALIGNED = "aligned"
    SPLIT_IDENTITY = "split_identity"
    STALE_CONNECTION = "stale_connection"
    STALE_HOST_AUTH = "stale_host_auth"
    HOST_NOT_CONFIGURED = "host_not_configured"
    HOST_CONFIG_UNREADABLE = "host_config_unreadable"
    LIVE_CONNECTION_MISSING = "live_connection_missing"
    RECONNECT_REQUIRED = "reconnect_required"
    UNSUPPORTED_HOST = "unsupported_host"
    SURFACE_UNAVAILABLE = "surface_unavailable"
    SCOPE_DENIED = "scope_denied"
    AMBIGUOUS_CONNECTION = "ambiguous_connection"
    NOT_DETECTED = "not_detected"


class ReconciliationMode(str, enum.Enum):
    """Doctor operating mode with host awareness (SDK-CLIENT-01-D §6)."""

    LOCAL_ONLY = "local_only"
    HOST_INVENTORY = "host_inventory"
    LIVE_RECONCILIATION = "live_reconciliation"


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
    INSTALL_HOST_CREDENTIALS = "install_host_credentials"
    REPAIR_HOST_CONFIG = "repair_host_config"
    REFRESH_HOST = "refresh_host"
    RESTART_HOST = "restart_host"
    RELOAD_MCP_EXTENSION = "reload_mcp_extension"
    RERUN_DOCTOR = "rerun_doctor"


class ReconnectRequirement(str, enum.Enum):
    """What the user must do after credential install (SDK-CLIENT-01-D §5)."""

    NONE = "none"
    RELOAD_WINDOW = "reload_window"
    RESTART_IDE = "restart_ide"
    RESTART_EXTENSION = "restart_extension"
    MANUAL = "manual"


# ── Host Record ──────────────────────────────────────────


class DoctorHostRecord(BaseModel):
    """Structured record for a single discovered host (§10.1).

    Extended in SDK-CLIENT-01-D with principal source and config path fields.
    """

    host_id: str
    host_type: HostType = HostType.UNKNOWN
    host_family: HostFamily = HostFamily.UNKNOWN
    display_name: str = ""
    detected: bool = False
    config_detected: bool = False
    config_path: str = ""
    keyhole_server_entry_detected: bool = False
    server_url: str = ""
    local_auth_hints_present: bool = False
    auth_source_mode: str = ""
    configured_principal_source: str = ""
    connection_visible_from_server: bool = False
    connection_id: str = ""
    server_principal_user_id: str = ""
    server_principal_label: str = ""
    staleness_state: StalenessState = StalenessState.UNKNOWN
    supports_rebind: bool = False
    supports_invalidate: bool = False
    support_status: HostSupportStatus = HostSupportStatus.UNKNOWN
    reconnect_requirement: ReconnectRequirement = ReconnectRequirement.NONE
    diagnosis: HostDiagnosis = HostDiagnosis.NOT_DETECTED

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for JSON output and proof artifacts."""
        return {
            "host_id": self.host_id,
            "host_type": self.host_type.value,
            "host_family": self.host_family.value,
            "display_name": self.display_name,
            "detected": self.detected,
            "config_detected": self.config_detected,
            "config_path": self.config_path,
            "keyhole_server_entry_detected": self.keyhole_server_entry_detected,
            "server_url": self.server_url,
            "local_auth_hints_present": self.local_auth_hints_present,
            "auth_source_mode": self.auth_source_mode,
            "configured_principal_source": self.configured_principal_source,
            "connection_visible_from_server": self.connection_visible_from_server,
            "connection_id": self.connection_id,
            "server_principal_user_id": self.server_principal_user_id,
            "server_principal_label": self.server_principal_label,
            "staleness_state": self.staleness_state.value,
            "supports_rebind": self.supports_rebind,
            "supports_invalidate": self.supports_invalidate,
            "support_status": self.support_status.value,
            "reconnect_requirement": self.reconnect_requirement.value,
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
    """Aggregated doctor report across all hosts (§10.2).

    Extended in SDK-CLIENT-01-D with reconciliation_mode and
    three-layer identity fields.
    """

    cli_active_profile: str = ""
    cli_user_id: str = ""
    reconciliation_mode: ReconciliationMode = ReconciliationMode.LOCAL_ONLY
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
            "reconciliation_mode": self.reconciliation_mode.value,
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


# ── SDK-CLIENT-23: Host Identity Attestation ─────────────


ATTESTATION_TTL_SECONDS = 600  # 10 minutes for confirmed attestations


class AttestationConfidence(str, enum.Enum):
    """How strongly the host inspector proved the principal's identity."""

    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNKNOWN = "unknown"


class CoherenceVerdict(str, enum.Enum):
    """Result of comparing CLI identity against host attestations."""

    ACCEPT_MATCH = "ACCEPT_MATCH"
    WARNING_NO_HOST_ATTESTATION = "WARNING_NO_HOST_ATTESTATION"
    WARNING_STALE_HOST_ATTESTATION = "WARNING_STALE_HOST_ATTESTATION"
    WARNING_UNKNOWN_HOST_IDENTITY = "WARNING_UNKNOWN_HOST_IDENTITY"
    REJECT_HOST_CONFLICT = "REJECT_HOST_CONFLICT"
    ACCEPT_INTENTIONAL_SPLIT = "ACCEPT_INTENTIONAL_SPLIT"


class HostIdentityAttestation(BaseModel):
    """Host-proven identity attestation (SDK-CLIENT-23 §A).

    Written by a host inspector after performing a live ``whoami``
    through the actual host-bound Keyhole connection.
    """

    schema_version: str = "1"
    host_kind: str
    host_display_name: str = ""
    integration_name: str = "keyhole"
    server_url: str = ""
    realm: str = ""
    effective_principal: str
    effective_subject: str = ""
    proof_method: str = "live_whoami"
    confidence: AttestationConfidence = AttestationConfidence.CONFIRMED
    observed_at: str  # ISO-8601
    expires_at: str  # ISO-8601
    machine_scope: str = ""
    workspace_scope: Optional[str] = None
    correlation_id: str = ""
    notes: str = ""
    tool_version: str = ""

    def is_fresh(self, now: Optional[datetime] = None) -> bool:
        """Return True if this attestation has not expired."""
        if now is None:
            from datetime import timezone as _tz
            now = datetime.now(_tz.utc)
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            now_aware = now if now.tzinfo else now.replace(
                tzinfo=exp.tzinfo
            )
            return now_aware <= exp
        except (ValueError, TypeError):
            return False

    def is_confirmed(self) -> bool:
        return self.confidence == AttestationConfidence.CONFIRMED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "host_kind": self.host_kind,
            "host_display_name": self.host_display_name,
            "integration_name": self.integration_name,
            "server_url": self.server_url,
            "realm": self.realm,
            "effective_principal": self.effective_principal,
            "effective_subject": self.effective_subject,
            "proof_method": self.proof_method,
            "confidence": self.confidence.value,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "machine_scope": self.machine_scope,
            "workspace_scope": self.workspace_scope,
            "correlation_id": self.correlation_id,
            "notes": self.notes,
            "tool_version": self.tool_version,
        }


class IdentityPolicyOverride(BaseModel):
    """Local split-identity override record (SDK-CLIENT-23 §G).

    Persisted in ``~/.keyhole/identity_policy.json`` to indicate
    the user intentionally allowed a principal mismatch.
    """

    override_type: str = "allow_split_identity"
    created_at: str  # ISO-8601
    target_principal: str
    conflicting_host_principal: str
    host_kind: str
    reason: str = ""
    expiry: Optional[str] = None  # ISO-8601, optional

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if not self.expiry:
            return False
        if now is None:
            from datetime import timezone as _tz
            now = datetime.now(_tz.utc)
        try:
            exp = datetime.fromisoformat(self.expiry.replace("Z", "+00:00"))
            now_aware = now if now.tzinfo else now.replace(
                tzinfo=exp.tzinfo
            )
            return now_aware > exp
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "override_type": self.override_type,
            "created_at": self.created_at,
            "target_principal": self.target_principal,
            "conflicting_host_principal": self.conflicting_host_principal,
            "host_kind": self.host_kind,
            "reason": self.reason,
            "expiry": self.expiry,
        }
