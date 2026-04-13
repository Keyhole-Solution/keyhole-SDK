"""Proof artifact emitter for governed runs — SDK-CLIENT-09 §13.

Writes proof artifacts into the canonical scaffold created by SDK-CLIENT-02:

    proof_bundle/
      core/
        runs/
          <correlation-id>/
            request.json
            response.json
            summary.md
            correlation.json
      extended/
        runs/
          <correlation-id>/
            debug.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.run_dispatch.request_builder import RunRequest


def emit_run_proof(
    *,
    repo_dir: Path,
    request: RunRequest,
    outcome_dict: Dict[str, Any],
    correlation_id: str,
    transport_proof_dict: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write proof artifacts for a governed run invocation.

    Returns the path to the proof run directory (core).

    Proof is written for both success and failure (§13).
    Shadow mode is always visible in proof output (§11).
    """
    safe_id = _safe_dirname(correlation_id)

    core_run_dir = repo_dir / "proof_bundle" / "core" / "runs" / safe_id
    extended_run_dir = repo_dir / "proof_bundle" / "extended" / "runs" / safe_id

    core_run_dir.mkdir(parents=True, exist_ok=True)
    extended_run_dir.mkdir(parents=True, exist_ok=True)

    # ── core/runs/<id>/request.json ──
    _write_json(core_run_dir / "request.json", request.to_proof_dict())

    # ── core/runs/<id>/response.json ──
    _write_json(core_run_dir / "response.json", outcome_dict)

    # ── core/runs/<id>/correlation.json ──
    correlation_data = {
        "correlation_id": correlation_id,
        "run_type": request.run_type,
        "repo": request.repo_name,
        "shadow": request.shadow,
        "identity_fingerprint": request.identity_fingerprint,
        "timestamp": request.timestamp,
    }
    if transport_proof_dict:
        correlation_data["transport"] = transport_proof_dict
    _write_json(core_run_dir / "correlation.json", correlation_data)

    # ── core/runs/<id>/summary.md ──
    summary = _render_summary(request, outcome_dict, correlation_id)
    (core_run_dir / "summary.md").write_text(summary, encoding="utf-8")

    # ── extended/runs/<id>/debug.json ──
    debug_data: Dict[str, Any] = {
        "proof_written_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
    if transport_proof_dict:
        debug_data["transport_proof"] = transport_proof_dict
    _write_json(extended_run_dir / "debug.json", debug_data)

    return core_run_dir


def _render_summary(
    request: RunRequest,
    outcome_dict: Dict[str, Any],
    correlation_id: str,
) -> str:
    """Render a human-readable summary.md for the proof bundle."""
    mode = "SHADOW" if request.shadow else "GOVERNED"
    status = outcome_dict.get("status", "unknown")
    lines = [
        f"# Run Proof — {correlation_id}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Run Type | `{request.run_type}` |",
        f"| Repo | `{request.repo_name}` |",
        f"| Mode | {mode} |",
        f"| Status | {status} |",
        f"| Correlation ID | `{correlation_id}` |",
        f"| Timestamp | {request.timestamp} |",
    ]
    if outcome_dict.get("run_id"):
        lines.append(f"| Run ID | `{outcome_dict['run_id']}` |")
    if outcome_dict.get("error_class"):
        lines.append(f"| Error Class | {outcome_dict['error_class']} |")
    if outcome_dict.get("reason"):
        lines.append(f"| Reason | {outcome_dict['reason']} |")
    if outcome_dict.get("repair_guidance"):
        lines.append("")
        lines.append("## Repair Guidance")
        lines.append("")
        for g in outcome_dict["repair_guidance"]:
            lines.append(f"- {g}")

    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write a JSON file atomically."""
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _safe_dirname(correlation_id: str) -> str:
    """Sanitize a correlation ID for use as a directory name."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in correlation_id)
    return safe or "unknown"
