"""Run status retrieval — SDK-CLIENT-17 §5.2/§10.

Retrieves current run state from the boundary via GovernedTransport.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from keyhole_sdk.run_lifecycle.models import (
    RunStatus,
    RunStatusResult,
    classify_status,
)


def fetch_run_status(
    *,
    transport: Any,  # GovernedTransport
    run_id: str,
    repo_name: str = "",
) -> RunStatusResult:
    """Retrieve the current state of a governed run.

    §10: Safe for repeated polling, uses READ_ONLY transport class.
    """
    try:
        result = transport.execute(
            "POST",
            "/mcp/v1/runs/start",
            operation_name="run.status",
            json={
                "run_type": "run.status",
                "params": {"run_id": run_id},
            },
        )
    except Exception as exc:
        return _handle_status_exception(exc, run_id)

    return _classify_status_result(result, run_id, repo_name)


def _classify_status_result(
    result: Any,
    run_id: str,
    repo_name: str,
) -> RunStatusResult:
    """Classify the boundary response into a RunStatusResult."""
    data = result.data if hasattr(result, "data") else {}
    status_code = result.status_code if hasattr(result, "status_code") else 0

    if status_code >= 400:
        from keyhole_sdk.run_lifecycle.repair import map_run_lifecycle_repair
        return RunStatusResult(
            success=False,
            run_id=run_id,
            status=RunStatus.UNKNOWN,
            error_class=data.get("error_class", "status_retrieval_failed"),
            reason=data.get("reason", data.get("message", f"HTTP {status_code}")),
            repair_guidance=map_run_lifecycle_repair("status_retrieval_failed"),
            response_data=data,
        )

    raw_status = (
        data.get("status", "")
        or data.get("state", "")
        or data.get("run_status", "")
    )
    classified = classify_status(raw_status)

    # Extract nested data if present
    nested = data.get("data", {}) if isinstance(data.get("data"), dict) else {}

    return RunStatusResult(
        success=True,
        run_id=data.get("run_id", run_id),
        status=classified,
        run_type=data.get("run_type", nested.get("run_type", "")),
        repo_name=data.get("repo", nested.get("repo", repo_name)),
        shadow=data.get("shadow", nested.get("shadow", False)),
        ctxpack_digest=data.get("ctxpack_digest", nested.get("ctxpack_digest", "")),
        last_updated=data.get("updated_at", data.get("last_updated", "")),
        summary=data.get("summary", nested.get("summary", "")),
        terminal_summary=data.get("terminal_summary", nested.get("result", "")),
        response_data=data,
    )


def _handle_status_exception(
    exc: Exception,
    run_id: str,
) -> RunStatusResult:
    """Convert transport exceptions into RunStatusResult."""
    from keyhole_sdk.run_lifecycle.repair import map_run_lifecycle_repair

    error_class = type(exc).__name__
    return RunStatusResult(
        success=False,
        run_id=run_id,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=map_run_lifecycle_repair(error_class),
    )
