"""SDK-CLIENT-01-D — Host identity diagnostics and classification (§13).

Pure functions for classifying host identity alignment and
building repair guidance.  No network calls — classification
operates on already-retrieved data.

Extended in SDK-CLIENT-01-D with:
  - HOST_NOT_CONFIGURED, HOST_CONFIG_UNREADABLE, STALE_HOST_AUTH
  - LIVE_CONNECTION_MISSING, RECONNECT_REQUIRED, SCOPE_DENIED
  - New repair guidance for credential installation and reconnect
"""
from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.doctor.models import (
    DoctorHostEntry,
    DoctorHostRecord,
    DoctorReport,
    DoctorSummaryStatus,
    HostDiagnosis,
    HostFamily,
    RecommendedAction,
    ReconnectRequirement,
    ReconciliationMode,
    RepairGuidance,
    StalenessState,
)


# ── Identity Classification (§13) ────────────────────────


def classify_host_diagnosis(
    *,
    cli_user_id: str,
    cli_profile_label: str,
    host_record: DoctorHostRecord,
    connection_surfaces_available: bool,
) -> HostDiagnosis:
    """Classify a host's identity alignment against the CLI profile.

    INV-SDK-CLIENT-01-C-001: Split identity is visible.
    INV-SDK-CLIENT-01-C-002: Login is not rebind.
    INV-SDK-CLIENT-01-C-005: Unsupported surfaces degrade honestly.
    INV-SDK-CLIENT-01-D-002: Split identity must be explicit.
    INV-SDK-CLIENT-01-D-005: Local success is NOT live success.
    """
    # Host not detected at all
    if not host_record.detected:
        return HostDiagnosis.NOT_DETECTED

    # Host detected but config unreadable
    if not host_record.config_detected:
        return HostDiagnosis.HOST_CONFIG_UNREADABLE

    # No Keyhole server entry in the host
    if not host_record.keyhole_server_entry_detected:
        return HostDiagnosis.HOST_NOT_CONFIGURED

    # Server connection surfaces not available
    if not connection_surfaces_available:
        return HostDiagnosis.SURFACE_UNAVAILABLE

    # Connection not visible from server
    if not host_record.connection_visible_from_server:
        return HostDiagnosis.LIVE_CONNECTION_MISSING

    # No server principal to compare
    if not host_record.server_principal_user_id:
        return HostDiagnosis.AMBIGUOUS_CONNECTION

    # §13.1 — Split identity detection
    if host_record.server_principal_user_id != cli_user_id:
        return HostDiagnosis.SPLIT_IDENTITY

    # Staleness check (SDK-CLIENT-01-D)
    if host_record.staleness_state == StalenessState.STALE_CONFIRMED:
        return HostDiagnosis.STALE_HOST_AUTH

    # §13.2 — Aligned state
    return HostDiagnosis.ALIGNED


def build_repair_guidance(
    host_record: DoctorHostRecord,
) -> RepairGuidance:
    """Build concrete repair guidance for a diagnosed host (§16).

    Extended in SDK-CLIENT-01-D with reconnect-aware guidance.
    """
    diagnosis = host_record.diagnosis
    host_id = host_record.host_id
    family = host_record.host_family

    if diagnosis == HostDiagnosis.NOT_DETECTED:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[RecommendedAction.INSTALL_HOST_ENTRY, RecommendedAction.RERUN_DOCTOR],
            descriptions=[
                "Verify the host is installed.",
                "Add a Keyhole MCP server entry to the host configuration.",
                "Rerun 'keyhole doctor' to verify.",
            ],
            commands=["keyhole host install --host " + host_id, "keyhole doctor"],
        )

    if diagnosis == HostDiagnosis.UNSUPPORTED_HOST:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            descriptions=[
                f"Host '{host_id}' was detected but is not supported for automated setup.",
                "Check host documentation for MCP server configuration.",
            ],
            actions=[RecommendedAction.RERUN_DOCTOR],
            commands=["keyhole doctor"],
        )

    if diagnosis == HostDiagnosis.HOST_CONFIG_UNREADABLE:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[RecommendedAction.REPAIR_HOST_CONFIG, RecommendedAction.RERUN_DOCTOR],
            descriptions=[
                f"Host '{host_id}' was detected but its configuration is unreadable.",
                "Check file permissions and JSON validity of the host config.",
            ],
            commands=[
                f"keyhole host inspect --host {host_id}",
                "keyhole doctor",
            ],
        )

    if diagnosis == HostDiagnosis.HOST_NOT_CONFIGURED:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.INSTALL_HOST_CREDENTIALS,
                RecommendedAction.RERUN_DOCTOR,
            ],
            descriptions=[
                f"Host '{host_id}' is installed but has no Keyhole MCP server entry.",
                "Install credentials to connect the host to the MCP boundary.",
                _reconnect_hint(family, host_record.reconnect_requirement),
            ],
            commands=[
                f"keyhole host install --host {host_id}",
                "keyhole doctor",
            ],
        )

    if diagnosis == HostDiagnosis.SURFACE_UNAVAILABLE:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.UPGRADE_SERVER,
                RecommendedAction.USE_GENERIC_WHOAMI,
            ],
            descriptions=[
                "The server does not support connection-truth surfaces.",
                "Upgrade the server or use 'keyhole whoami' for generic identity.",
                "Do not assume host alignment without server confirmation.",
            ],
            commands=["keyhole whoami"],
        )

    if diagnosis == HostDiagnosis.STALE_CONNECTION:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.REFRESH_HOST,
                RecommendedAction.INVALIDATE_RECONNECT,
            ],
            descriptions=[
                "The host connection is not visible from the server.",
                "Ensure the host has opened a Keyhole connection.",
                "Refresh the host or invalidate and reconnect.",
                _reconnect_hint(family, host_record.reconnect_requirement),
            ],
            commands=[
                "keyhole connections list",
                f"keyhole connection invalidate --host {host_id} --yes",
            ],
        )

    if diagnosis == HostDiagnosis.LIVE_CONNECTION_MISSING:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.REFRESH_HOST,
                RecommendedAction.RESTART_HOST,
            ],
            descriptions=[
                "Host has Keyhole entry but no live connection is visible from the server.",
                "The host may need to reconnect.",
                _reconnect_hint(family, host_record.reconnect_requirement),
            ],
            commands=[
                f"keyhole host inspect --host {host_id}",
                "keyhole connections list",
            ],
        )

    if diagnosis == HostDiagnosis.STALE_HOST_AUTH:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.REFRESH_HOST,
                RecommendedAction.INSTALL_HOST_CREDENTIALS,
            ],
            descriptions=[
                "Host identity is aligned but the auth token may be stale.",
                "Refresh or reinstall credentials.",
                _reconnect_hint(family, host_record.reconnect_requirement),
            ],
            commands=[
                f"keyhole host install --host {host_id} --force",
            ],
        )

    if diagnosis == HostDiagnosis.RECONNECT_REQUIRED:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[RecommendedAction.RESTART_HOST, RecommendedAction.RELOAD_MCP_EXTENSION],
            descriptions=[
                "Credentials were updated but the host needs to reconnect.",
                _reconnect_hint(family, host_record.reconnect_requirement),
            ],
            commands=[],
        )

    if diagnosis == HostDiagnosis.SCOPE_DENIED:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[RecommendedAction.RERUN_DOCTOR],
            descriptions=[
                "The host connection was rejected by the server due to scope.",
                "Check the host's charter and workspace configuration.",
            ],
            commands=["keyhole doctor"],
        )

    if diagnosis == HostDiagnosis.SPLIT_IDENTITY:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[
                RecommendedAction.KEEP_AS_IS,
                RecommendedAction.REBIND,
                RecommendedAction.INVALIDATE_RECONNECT,
            ],
            descriptions=[
                f"CLI profile and host '{host_id}' are executing as different principals.",
                "Keep the current host identity, rebind to the active profile, "
                "or invalidate the connection and reconnect.",
            ],
            commands=[
                f"keyhole connection rebind --host {host_id} --profile <profile>",
                f"keyhole connection invalidate --host {host_id} --yes",
            ],
        )

    if diagnosis == HostDiagnosis.AMBIGUOUS_CONNECTION:
        return RepairGuidance(
            host_id=host_id,
            diagnosis=diagnosis,
            actions=[RecommendedAction.RERUN_DOCTOR],
            descriptions=[
                "The server returned an ambiguous connection identity.",
                "Retry the doctor scan or inspect the connection directly.",
            ],
            commands=[
                f"keyhole connection inspect --host {host_id}",
                "keyhole doctor",
            ],
        )

    # ALIGNED — no repair needed
    return RepairGuidance(
        host_id=host_id,
        diagnosis=diagnosis,
        descriptions=["No action required — host identity is aligned."],
    )


def _reconnect_hint(family: HostFamily, requirement: ReconnectRequirement) -> str:
    """Build a human-readable reconnect hint for a host family."""
    hints = {
        ReconnectRequirement.RELOAD_WINDOW: "Reload the VS Code window (Ctrl+Shift+P → 'Reload Window').",
        ReconnectRequirement.RESTART_IDE: "Restart the IDE to pick up config changes.",
        ReconnectRequirement.RESTART_EXTENSION: "Restart the MCP extension.",
        ReconnectRequirement.MANUAL: "Follow host documentation for reconnection steps.",
    }
    return hints.get(requirement, "")


# ── Report Builder ────────────────────────────────────────


def build_doctor_report(
    *,
    cli_active_profile: str,
    cli_user_id: str,
    host_records: List[DoctorHostRecord],
    connection_surfaces_available: bool,
    negotiation_available: bool,
    reconciliation_mode: ReconciliationMode = ReconciliationMode.LOCAL_ONLY,
    correlation_id: str = "",
) -> DoctorReport:
    """Build an aggregated doctor report from classified hosts (§10.2)."""
    entries: List[DoctorHostEntry] = []

    for record in host_records:
        # Classify if not already diagnosed
        if record.diagnosis == HostDiagnosis.NOT_DETECTED and record.detected:
            record.diagnosis = classify_host_diagnosis(
                cli_user_id=cli_user_id,
                cli_profile_label=cli_active_profile,
                host_record=record,
                connection_surfaces_available=connection_surfaces_available,
            )

        guidance = build_repair_guidance(record)

        entries.append(
            DoctorHostEntry(
                host_id=record.host_id,
                diagnosis=record.diagnosis,
                current_connection_principal=record.server_principal_label,
                recommended_actions=guidance.actions,
            )
        )

    # Determine summary status
    statuses = [e.diagnosis for e in entries]
    if HostDiagnosis.SPLIT_IDENTITY in statuses:
        summary = DoctorSummaryStatus.ATTENTION_REQUIRED
    elif any(
        s
        in (
            HostDiagnosis.STALE_CONNECTION,
            HostDiagnosis.STALE_HOST_AUTH,
            HostDiagnosis.LIVE_CONNECTION_MISSING,
            HostDiagnosis.HOST_NOT_CONFIGURED,
            HostDiagnosis.HOST_CONFIG_UNREADABLE,
            HostDiagnosis.RECONNECT_REQUIRED,
            HostDiagnosis.AMBIGUOUS_CONNECTION,
            HostDiagnosis.SURFACE_UNAVAILABLE,
        )
        for s in statuses
    ):
        summary = DoctorSummaryStatus.DEGRADED
    else:
        summary = DoctorSummaryStatus.OK

    return DoctorReport(
        cli_active_profile=cli_active_profile,
        cli_user_id=cli_user_id,
        reconciliation_mode=reconciliation_mode,
        hosts=entries,
        host_records=host_records,
        summary_status=summary,
        negotiation_available=negotiation_available,
        connection_surfaces_available=connection_surfaces_available,
        correlation_id=correlation_id,
    )
