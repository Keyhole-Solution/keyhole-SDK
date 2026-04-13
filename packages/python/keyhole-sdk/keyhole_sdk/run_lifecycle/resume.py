"""Run resume — SDK-CLIENT-17 §5.5/§13.

Reconnect the builder to an existing governed run identity.
Resume is "reconnect to the same governed execution" — NOT "run again."

Must avoid accidental duplicate execution and preserve original proof lineage.
"""

from __future__ import annotations

from typing import Any, Optional

from keyhole_sdk.run_lifecycle.models import (
    RunStatus,
    RunResumeResult,
    classify_status,
)
from keyhole_sdk.run_lifecycle.record import LocalRunRecordStore, RunRecord
from keyhole_sdk.run_lifecycle.status import fetch_run_status


def resume_run(
    *,
    transport: Any,  # GovernedTransport
    identifier: str,
    repo_dir: Any,  # Path
    repo_name: str = "",
) -> RunResumeResult:
    """Resume connection to an existing governed run.

    §13: Resume reconnects — it does not re-execute.
    Uses local run records first, then falls back to boundary lookup.
    If ambiguity exists, surfaces it clearly with repair steps.
    """
    from pathlib import Path
    repo_path = Path(repo_dir)

    if not identifier or not identifier.strip():
        return RunResumeResult(
            success=False,
            error_class="missing_identifier",
            reason="No run ID or request ID provided.",
            repair_guidance=[
                "Provide a run-id or request-id to resume.",
                "List recent runs with: keyhole runs list",
            ],
        )

    identifier = identifier.strip()

    # ── Step 1: Check local run records ──
    store = LocalRunRecordStore(repo_path)
    local_record = store.load(identifier)

    if local_record is not None:
        run_id = local_record.run_id or identifier
        # Try to get current status from boundary
        status_result = fetch_run_status(
            transport=transport,
            run_id=run_id,
            repo_name=local_record.repo_name or repo_name,
        )

        if status_result.success:
            # Update local record with current status
            store.update_status(
                local_record.run_id or local_record.request_id or local_record.correlation_id,
                status_result.status.value,
            )
            return RunResumeResult(
                success=True,
                run_id=status_result.run_id or run_id,
                status=status_result.status,
                reconnected=True,
                source="local_record",
                response_data=status_result.response_data,
            )
        else:
            # Local record found but boundary lookup failed
            # Still succeed with local info — observation failure ≠ execution failure
            return RunResumeResult(
                success=True,
                run_id=run_id,
                status=classify_status(local_record.last_known_status),
                reconnected=True,
                source="local_record",
                response_data={
                    "note": "Reconnected from local record. Boundary status unavailable.",
                    "last_known_status": local_record.last_known_status,
                },
                repair_guidance=[
                    f"Check boundary status: keyhole runs status {run_id}",
                    "Observation failure does not mean execution failed.",
                ],
            )

    # ── Step 2: Try boundary lookup directly ──
    status_result = fetch_run_status(
        transport=transport,
        run_id=identifier,
        repo_name=repo_name,
    )

    if status_result.success:
        # Found on boundary — create local record for future resume
        record = RunRecord(
            run_id=status_result.run_id or identifier,
            run_type=status_result.run_type,
            repo_name=status_result.repo_name or repo_name,
            last_known_status=status_result.status.value,
            ctxpack_digest=status_result.ctxpack_digest,
        )
        try:
            store.save(record)
        except (OSError, ValueError):
            pass

        return RunResumeResult(
            success=True,
            run_id=status_result.run_id or identifier,
            status=status_result.status,
            reconnected=True,
            source="boundary_lookup",
            response_data=status_result.response_data,
        )

    # ── Step 3: Neither local nor boundary found ──
    from keyhole_sdk.run_lifecycle.repair import map_run_lifecycle_repair
    return RunResumeResult(
        success=False,
        run_id=identifier,
        error_class="resume_ambiguous",
        reason=f"Cannot locate run '{identifier}' locally or on the boundary.",
        repair_guidance=map_run_lifecycle_repair("resume_ambiguous"),
    )
