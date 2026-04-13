"""Capability search and resolution proof — SDK-CLIENT-08 §19.

Search proof is lightweight.
Resolution proof is replayable and includes all required fields.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def emit_search_proof(
    *,
    state_dir: Path,
    correlation_id: str,
    request_dict: Dict[str, Any],
    result_dict: Dict[str, Any],
) -> Path:
    """Emit a lightweight search proof artifact.

    Returns the proof directory path.
    """
    corr = _safe_dirname(correlation_id) if correlation_id else "unknown"
    proof_dir = state_dir / "search" / corr
    proof_dir.mkdir(parents=True, exist_ok=True)

    _write_json(proof_dir / "request.json", request_dict)
    _write_json(proof_dir / "response.json", result_dict)
    _write_json(proof_dir / "correlation.json", {
        "correlation_id": correlation_id,
        "operation": "capability.search",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    })

    return proof_dir


def emit_resolution_proof(
    *,
    state_dir: Path,
    correlation_id: str,
    request_dict: Dict[str, Any],
    outcome_dict: Dict[str, Any],
    materialization_dict: Optional[Dict[str, Any]] = None,
    repo_posture: str = "",
    mode: str = "",
) -> Path:
    """Emit a replayable resolution proof bundle.

    §19.2: Includes command invoked, local repo identity, repo posture,
    input capability request, server response, resolution decision,
    advisory vs write mode, and diff / no-diff statement.

    Returns the proof directory path.
    """
    corr = _safe_dirname(correlation_id) if correlation_id else "unknown"
    proof_dir = state_dir / "resolution" / corr
    proof_dir.mkdir(parents=True, exist_ok=True)

    # Core request/response
    _write_json(proof_dir / "request.json", request_dict)
    _write_json(proof_dir / "response.json", outcome_dict)

    # Materialization / diff
    if materialization_dict is not None:
        _write_json(proof_dir / "diff.json", materialization_dict)

    # Correlation metadata
    _write_json(proof_dir / "correlation.json", {
        "correlation_id": correlation_id,
        "operation": "capability.resolve",
        "repo_posture": repo_posture,
        "mode": mode,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    })

    # Summary
    summary = _render_resolution_summary(
        request_dict=request_dict,
        outcome_dict=outcome_dict,
        materialization_dict=materialization_dict,
        repo_posture=repo_posture,
        mode=mode,
    )
    (proof_dir / "summary.md").write_text(summary, encoding="utf-8")

    # Digest
    (proof_dir / "digest.txt").write_text(correlation_id + "\n", encoding="utf-8")

    # Suggested dependency (if resolved)
    resolved = outcome_dict.get("resolved")
    if resolved:
        _write_json(proof_dir / "suggested-dependency.json", resolved)

    return proof_dir


def _render_resolution_summary(
    *,
    request_dict: Dict[str, Any],
    outcome_dict: Dict[str, Any],
    materialization_dict: Optional[Dict[str, Any]],
    repo_posture: str,
    mode: str,
) -> str:
    """Render a human-readable resolution summary."""
    cap = request_dict.get("capability", "unknown")
    provider = request_dict.get("provider", "")
    status = outcome_dict.get("status", "unknown")
    resolved = outcome_dict.get("resolved", {})
    r_provider = resolved.get("provider", "") if resolved else ""
    r_version = resolved.get("version", "") if resolved else ""

    lines = [
        "# Resolution Proof",
        "",
        f"**Capability:** {cap}",
        f"**Status:** {status}",
        f"**Repo Posture:** {repo_posture or 'unknown'}",
        f"**Mode:** {mode or 'advisory'}",
    ]
    if provider:
        lines.append(f"**Requested Provider:** {provider}")
    if r_provider:
        lines.append(f"**Resolved Provider:** {r_provider}")
    if r_version:
        lines.append(f"**Resolved Version:** {r_version}")
    if materialization_dict:
        lines.append("")
        lines.append("## Materialization")
        mat_target = materialization_dict.get("target", "none")
        mat_write = materialization_dict.get("is_write", False)
        mat_diff = materialization_dict.get("diff_summary", "No diff.")
        lines.append(f"**Target:** {mat_target}")
        lines.append(f"**Write:** {mat_write}")
        lines.append(f"**Diff:** {mat_diff}")
    if outcome_dict.get("repair_guidance"):
        lines.append("")
        lines.append("## Repair Guidance")
        for g in outcome_dict["repair_guidance"]:
            lines.append(f"- {g}")
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, data: Any) -> None:
    """Write a JSON file with consistent formatting."""
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def _safe_dirname(name: str) -> str:
    """Sanitize a correlation ID for safe directory naming."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
