"""Run lifecycle proof — SDK-CLIENT-17 §15.

Persists lifecycle proof artifacts under the canonical proof structure:

    proof_bundle/
      core/
        runs/<run-id-or-request-id>/
          accepted.json
          latest-status.json
          outcome.json
          correlation.json
          summary.md
      extended/
        runs/<run-id-or-request-id>/
          events.json
          debug.json

Extends — does not replace — the proof lineage from SDK-CLIENT-09.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def emit_run_lifecycle_proof(
    *,
    repo_dir: Path,
    run_id: str,
    stage: str,
    data: Dict[str, Any],
    correlation_id: str = "",
) -> Path:
    """Write a lifecycle proof artifact for a governed run.

    Args:
        repo_dir: Root of the governed repo.
        run_id: The run identity to file under.
        stage: Proof stage — "accepted", "latest-status", "outcome",
               "events", or "debug".
        data: The data to persist.
        correlation_id: Original correlation/request ID.

    Returns the directory path where the proof was written.
    """
    safe_id = _safe_dirname(run_id or correlation_id)

    # Determine core vs extended
    if stage in ("accepted", "latest-status", "outcome", "correlation", "summary"):
        run_dir = repo_dir / "proof_bundle" / "core" / "runs" / safe_id
    else:
        run_dir = repo_dir / "proof_bundle" / "extended" / "runs" / safe_id

    run_dir.mkdir(parents=True, exist_ok=True)

    # Write the artifact
    filename = f"{stage}.json"
    artifact = {
        "stage": stage,
        "run_id": run_id,
        "correlation_id": correlation_id,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    artifact.update(data)

    _write_json(run_dir / filename, artifact)

    # Write/update summary.md for terminal outcomes
    if stage == "outcome":
        _write_outcome_summary(run_dir, run_id, data, correlation_id)

    return run_dir


def emit_accepted_proof(
    *,
    repo_dir: Path,
    run_id: str,
    correlation_id: str = "",
    run_type: str = "",
    shadow: bool = False,
    ctxpack_digest: str = "",
    response_data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Convenience: emit proof for an accepted/deferred run at submission time."""
    data: Dict[str, Any] = {
        "run_type": run_type,
        "shadow": shadow,
        "ctxpack_digest": ctxpack_digest,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
    if response_data:
        data["response"] = response_data
    return emit_run_lifecycle_proof(
        repo_dir=repo_dir,
        run_id=run_id,
        stage="accepted",
        data=data,
        correlation_id=correlation_id,
    )


def emit_status_proof(
    *,
    repo_dir: Path,
    run_id: str,
    status: str,
    correlation_id: str = "",
    response_data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Convenience: emit proof for a status observation."""
    data: Dict[str, Any] = {
        "observed_status": status,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    if response_data:
        data["response"] = response_data
    return emit_run_lifecycle_proof(
        repo_dir=repo_dir,
        run_id=run_id,
        stage="latest-status",
        data=data,
        correlation_id=correlation_id,
    )


def emit_outcome_proof(
    *,
    repo_dir: Path,
    run_id: str,
    terminal_status: str,
    correlation_id: str = "",
    final_data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Convenience: emit proof for the terminal outcome."""
    data: Dict[str, Any] = {
        "terminal_status": terminal_status,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    if final_data:
        data["final"] = final_data
    return emit_run_lifecycle_proof(
        repo_dir=repo_dir,
        run_id=run_id,
        stage="outcome",
        data=data,
        correlation_id=correlation_id,
    )


def _write_outcome_summary(
    run_dir: Path,
    run_id: str,
    data: Dict[str, Any],
    correlation_id: str,
) -> None:
    """Write a human-readable summary.md for a terminal outcome."""
    terminal = data.get("terminal_status", "unknown")
    lines = [
        f"# Run Outcome — {run_id}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Run ID | `{run_id}` |",
        f"| Correlation ID | `{correlation_id}` |",
        f"| Terminal Status | {terminal} |",
        f"| Resolved At | {data.get('resolved_at', 'unknown')} |",
    ]
    if data.get("final"):
        lines.append("")
        lines.append("## Final Data")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(data["final"], indent=2, default=str))
        lines.append("```")
    lines.append("")
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write a JSON file."""
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _safe_dirname(key: str) -> str:
    """Sanitize a key for use as a directory name."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:128]
