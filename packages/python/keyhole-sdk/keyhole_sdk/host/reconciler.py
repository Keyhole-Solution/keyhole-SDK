"""SDK-CLIENT-01-D — Three-layer identity reconciler (§4).

Compares three identity layers:
  1. CLI active profile (local credential store)
  2. Host configured principal (from IDE config)
  3. Server live principal (from connection.identity.inspect)

Produces a structured verdict for display in `keyhole doctor`.

INV-SDK-CLIENT-01-D-002: Split identity must be explicit.
INV-SDK-CLIENT-01-D-005: Local success is NOT live success.
INV-SDK-CLIENT-01-D-006: Live truth comes from server surfaces.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from keyhole_sdk.doctor.models import (
    DoctorHostRecord,
    HostDiagnosis,
    HostFamily,
    RecommendedAction,
    ReconciliationMode,
    StalenessState,
)


@dataclass
class ThreeLayerIdentity:
    """Three-layer identity snapshot for a single host."""

    host_id: str
    host_family: HostFamily = HostFamily.UNKNOWN

    # Layer 1: CLI
    cli_user_id: str = ""
    cli_profile_label: str = ""

    # Layer 2: Host config
    host_configured_principal: str = ""
    host_auth_mode: str = ""

    # Layer 3: Server live
    server_user_id: str = ""
    server_principal_label: str = ""
    server_connection_id: str = ""
    server_staleness: StalenessState = StalenessState.UNKNOWN

    # Verdict
    diagnosis: HostDiagnosis = HostDiagnosis.NOT_DETECTED
    recommended_actions: List[RecommendedAction] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host_id": self.host_id,
            "host_family": self.host_family.value,
            "cli_user_id": self.cli_user_id,
            "cli_profile_label": self.cli_profile_label,
            "host_configured_principal": self.host_configured_principal,
            "host_auth_mode": self.host_auth_mode,
            "server_user_id": self.server_user_id,
            "server_principal_label": self.server_principal_label,
            "server_connection_id": self.server_connection_id,
            "server_staleness": self.server_staleness.value,
            "diagnosis": self.diagnosis.value,
            "recommended_actions": [a.value for a in self.recommended_actions],
            "description": self.description,
        }


def reconcile_three_layer(
    *,
    cli_user_id: str,
    cli_profile_label: str,
    host_record: DoctorHostRecord,
    connection_surfaces_available: bool,
) -> ThreeLayerIdentity:
    """Compare the three identity layers for a single host.

    Returns a ThreeLayerIdentity with diagnosis and recommended actions.
    """
    identity = ThreeLayerIdentity(
        host_id=host_record.host_id,
        host_family=host_record.host_family,
        cli_user_id=cli_user_id,
        cli_profile_label=cli_profile_label,
        host_configured_principal=host_record.configured_principal_source,
        host_auth_mode=host_record.auth_source_mode,
        server_user_id=host_record.server_principal_user_id,
        server_principal_label=host_record.server_principal_label,
        server_connection_id=host_record.connection_id,
        server_staleness=host_record.staleness_state,
    )

    # Not detected
    if not host_record.detected:
        identity.diagnosis = HostDiagnosis.NOT_DETECTED
        identity.description = "Host not detected on this machine."
        return identity

    # Config not readable
    if not host_record.config_detected:
        identity.diagnosis = HostDiagnosis.HOST_CONFIG_UNREADABLE
        identity.recommended_actions = [RecommendedAction.REPAIR_HOST_CONFIG]
        identity.description = "Host detected but config is unreadable."
        return identity

    # No Keyhole entry in host
    if not host_record.keyhole_server_entry_detected:
        identity.diagnosis = HostDiagnosis.HOST_NOT_CONFIGURED
        identity.recommended_actions = [
            RecommendedAction.INSTALL_HOST_CREDENTIALS,
        ]
        identity.description = "Host detected but no Keyhole MCP server entry configured."
        return identity

    # Server surfaces not available — can only do local comparison
    if not connection_surfaces_available:
        identity.diagnosis = HostDiagnosis.SURFACE_UNAVAILABLE
        identity.recommended_actions = [RecommendedAction.UPGRADE_SERVER]
        identity.description = (
            "Connection surfaces not available. "
            "Cannot verify live identity alignment."
        )
        return identity

    # No server connection visible
    if not host_record.connection_visible_from_server:
        identity.diagnosis = HostDiagnosis.LIVE_CONNECTION_MISSING
        identity.recommended_actions = [
            RecommendedAction.REFRESH_HOST,
            RecommendedAction.RESTART_HOST,
        ]
        identity.description = (
            "Host has Keyhole entry but no live connection visible from server."
        )
        return identity

    # Server returned empty principal
    if not host_record.server_principal_user_id:
        identity.diagnosis = HostDiagnosis.AMBIGUOUS_CONNECTION
        identity.recommended_actions = [RecommendedAction.RERUN_DOCTOR]
        identity.description = "Server returned ambiguous connection identity."
        return identity

    # Three-layer comparison
    cli_matches_server = (host_record.server_principal_user_id == cli_user_id)

    if cli_matches_server:
        # Staleness check
        if host_record.staleness_state == StalenessState.STALE_CONFIRMED:
            identity.diagnosis = HostDiagnosis.STALE_HOST_AUTH
            identity.recommended_actions = [
                RecommendedAction.REFRESH_HOST,
            ]
            identity.description = (
                "Identity aligned but host auth may be stale."
            )
        else:
            identity.diagnosis = HostDiagnosis.ALIGNED
            identity.description = "All three identity layers are aligned."
    else:
        identity.diagnosis = HostDiagnosis.SPLIT_IDENTITY
        identity.recommended_actions = [
            RecommendedAction.KEEP_AS_IS,
            RecommendedAction.REBIND,
            RecommendedAction.INVALIDATE_RECONNECT,
        ]
        identity.description = (
            f"CLI profile ({cli_user_id}) and server connection "
            f"({host_record.server_principal_user_id}) are different principals."
        )

    return identity
