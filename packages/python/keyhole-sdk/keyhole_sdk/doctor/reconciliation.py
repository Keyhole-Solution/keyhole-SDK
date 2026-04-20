"""SDK-CLIENT-01-D — Reconciliation flow orchestrator (§12).

Coordinates the full doctor reconciliation sequence:
  1. Determine CLI active profile
  2. Inventory local hosts
  3. Negotiate server capabilities
  4. Retrieve connection truth for visible hosts
  5. Compare identities and classify
  6. Build report with repair guidance
  7. Emit proof artifacts

INV-SDK-CLIENT-01-C-002: Login is not rebind.
INV-SDK-CLIENT-01-C-003: Doctor is advisory by default.
INV-SDK-CLIENT-01-C-004: Reconciliation is server-verified.
INV-SDK-CLIENT-01-D-005: Local success is NOT live success.
INV-SDK-CLIENT-01-D-006: Live truth comes from server surfaces.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from keyhole_sdk.doctor.diagnostics import (
    build_doctor_report,
    classify_host_diagnosis,
)
from keyhole_sdk.doctor.host_inventory import HostDetector, detect_hosts
from keyhole_sdk.doctor.models import (
    DoctorHostRecord,
    DoctorReport,
    HostDiagnosis,
    ReconciliationMode,
    StalenessState,
)


# ── Connection surface names (§9) ─────────────────────────

CONNECTION_LIST_RUN_TYPE = "connection.list.inspect"
CONNECTION_INSPECT_RUN_TYPE = "connection.identity.inspect"
CONNECTION_STATUS_RUN_TYPE = "connection.status.inspect"
CONNECTION_LINEAGE_RUN_TYPE = "connection.lineage.inspect"
CONNECTION_REBIND_RUN_TYPE = "connection.rebind"
CONNECTION_INVALIDATE_RUN_TYPE = "connection.invalidate"

# Legacy alias (back-compat)
CONNECTION_WHOAMI_RUN_TYPE = CONNECTION_INSPECT_RUN_TYPE

CONNECTION_SURFACES = frozenset(
    {
        CONNECTION_LIST_RUN_TYPE,
        CONNECTION_INSPECT_RUN_TYPE,
        CONNECTION_STATUS_RUN_TYPE,
        CONNECTION_LINEAGE_RUN_TYPE,
        CONNECTION_REBIND_RUN_TYPE,
        CONNECTION_INVALIDATE_RUN_TYPE,
    }
)


def check_connection_surfaces_available(
    server_operations: List[str],
    connection_surfaces: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if the server advertises connection-truth surfaces (§6.8).

    INV-SDK-CLIENT-01-C-008: Surface remains governed.

    Parameters
    ----------
    server_operations:
        Top-level operations list from capabilities.
    connection_surfaces:
        Raw ``connection_surfaces`` dict from capabilities (SDK-SERVER-01-C).
        When the server advertises connection ops under ``connection_surfaces``
        rather than the top-level ``operations`` array, this parameter carries
        them.
    """
    ops = set(server_operations)
    # Merge connection_surfaces.run_types if provided (SDK-SERVER-01-C)
    if connection_surfaces and isinstance(connection_surfaces, dict):
        for rt in connection_surfaces.get("run_types", []):
            if isinstance(rt, dict):
                name = rt.get("run_type", "")
                if name:
                    ops.add(name)
            elif isinstance(rt, str):
                ops.add(rt)
    # At minimum, connection.identity.inspect must be present
    return CONNECTION_INSPECT_RUN_TYPE in ops


def reconcile(
    *,
    cli_active_profile: str,
    cli_user_id: str,
    host_records: List[DoctorHostRecord],
    server_operations: Optional[List[str]] = None,
    connection_surfaces: Optional[Dict[str, Any]] = None,
    connection_truth: Optional[Dict[str, Dict[str, Any]]] = None,
    reconciliation_mode: ReconciliationMode = ReconciliationMode.LOCAL_ONLY,
    correlation_id: Optional[str] = None,
) -> DoctorReport:
    """Run the identity reconciliation flow (§12.1).

    Parameters
    ----------
    cli_active_profile:
        The builder's current CLI profile label.
    cli_user_id:
        The builder's current CLI user ID.
    host_records:
        Discovered host records from host inventory.
    server_operations:
        Operations list from capabilities (for surface negotiation).
    connection_surfaces:
        Raw ``connection_surfaces`` dict from capabilities (SDK-SERVER-01-C).
        When the server advertises connection ops under ``connection_surfaces``
        rather than the top-level ``operations`` array, pass this so the
        doctor can negotiate surfaces correctly.
    connection_truth:
        Optional dict of host_id → server connection data, retrieved
        from connection.whoami per host.
    reconciliation_mode:
        Doctor operating mode: local_only, host_inventory, or live_reconciliation.
    correlation_id:
        Optional correlation ID for proof/support tracing.
    """
    cid = correlation_id or str(uuid.uuid4())
    ops = server_operations or []
    conn_truth = connection_truth or {}

    # §6.8 — negotiate surface availability
    # INV-SDK-CLIENT-01-C-008: Surface remains governed
    surfaces_available = check_connection_surfaces_available(
        ops, connection_surfaces=connection_surfaces
    )

    # Enrich host records with connection truth where available
    for record in host_records:
        if not record.detected:
            continue

        host_data = conn_truth.get(record.host_id, {})
        if host_data:
            record.connection_visible_from_server = True
            record.connection_id = host_data.get("connection_id", "")
            record.server_principal_user_id = host_data.get("user_id", "")
            record.server_principal_label = host_data.get("principal", "")
            record.supports_rebind = host_data.get("supports_rebind", False)
            record.supports_invalidate = host_data.get("supports_invalidate", False)

            # Staleness
            if record.server_principal_user_id == cli_user_id:
                record.staleness_state = StalenessState.FRESH
            elif record.server_principal_user_id:
                record.staleness_state = StalenessState.STALE_CONFIRMED
            else:
                record.staleness_state = StalenessState.UNKNOWN

        # Classify
        record.diagnosis = classify_host_diagnosis(
            cli_user_id=cli_user_id,
            cli_profile_label=cli_active_profile,
            host_record=record,
            connection_surfaces_available=surfaces_available,
        )

    return build_doctor_report(
        cli_active_profile=cli_active_profile,
        cli_user_id=cli_user_id,
        host_records=host_records,
        connection_surfaces_available=surfaces_available,
        negotiation_available=len(ops) > 0,
        reconciliation_mode=reconciliation_mode,
        correlation_id=cid,
    )
