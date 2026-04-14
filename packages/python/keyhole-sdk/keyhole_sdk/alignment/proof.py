"""Alignment guidance proof emitter — SDK-CLIENT-11 §15.

Writes proof artifacts for alignment guidance to a tool-owned
local state directory (NOT into the target repo by default).

§15.2 Structure:
  <state_dir>/alignment/<analysis-id-or-request-id>/
    gap_analysis.json
    next_actions.json
    summary.md
    correlation.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.alignment.models import AlignmentGuidanceResult, GuidanceState


def emit_alignment_proof(
    *,
    state_dir: Path,
    correlation_id: str,
    request_dict: Dict[str, Any],
    result: AlignmentGuidanceResult,
) -> Path:
    """Write proof artifacts for an alignment guidance session.

    Proof is written for both success and partial-failure cases
    when usable analysis exists (§15 — "artifacts must be generated
    for success and partial-failure cases when usable analysis exists").

    Args:
        state_dir: Tool-owned state directory (e.g. ~/.keyhole/state).
        correlation_id: Correlation ID for this guidance request.
        request_dict: Proof-safe request data (from request.to_proof_dict()).
        result: The AlignmentGuidanceResult to persist.

    Returns:
        Path to the proof directory.
    """
    safe_id = _safe_dirname(correlation_id)
    proof_dir = state_dir / "alignment" / safe_id
    proof_dir.mkdir(parents=True, exist_ok=True)

    # ── gap_analysis.json ────────────────────────────────────────────────────
    # Verified vs inferred explicitly separated
    verified_items = [i.to_dict() for i in result.items if i.state == GuidanceState.VERIFIED]
    inferred_items = [i.to_dict() for i in result.items if i.state == GuidanceState.INFERRED]

    gap_analysis = {
        "readiness": result.readiness.value,
        "verified": verified_items,
        "inferred": inferred_items,
        "verified_count": result.verified_count,
        "inferred_count": result.inferred_count,
        "gap_count": result.gap_count,
        "warning_count": result.warning_count,
        "suggestion_count": result.suggestion_count,
        "no_mutation_applied": result.no_mutation_applied,
        "analysis_mode": result.analysis_mode,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(proof_dir / "gap_analysis.json", gap_analysis)

    # ── next_actions.json ────────────────────────────────────────────────────
    next_actions = {
        "next_best_action": result.next_best_action,
        "repair_guidance": result.repair_guidance,
        "readiness": result.readiness.value,
        "correlation_id": correlation_id,
    }
    _write_json(proof_dir / "next_actions.json", next_actions)

    # ── correlation.json ─────────────────────────────────────────────────────
    correlation_data: Dict[str, Any] = {
        "correlation_id": correlation_id,
        "proof_written_at": datetime.now(timezone.utc).isoformat(),
        "run_id": result.run_id,
        "analysis_mode": result.analysis_mode,
        "request_summary": {
            k: v
            for k, v in request_dict.items()
            if k in ("repo_identity", "analysis_id", "shadow", "correlation_id", "timestamp")
        } if isinstance(request_dict, dict) else {},
    }
    _write_json(proof_dir / "correlation.json", correlation_data)

    # ── summary.md ───────────────────────────────────────────────────────────
    summary_text = _render_summary(
        correlation_id=correlation_id,
        result=result,
        request_dict=request_dict,
    )
    (proof_dir / "summary.md").write_text(summary_text, encoding="utf-8")

    return proof_dir


def _render_summary(
    *,
    correlation_id: str,
    result: AlignmentGuidanceResult,
    request_dict: Dict[str, Any],
) -> str:
    """Render a human-readable summary.md for alignment guidance proof."""
    lines = [
        "# Alignment Guidance — SDK-CLIENT-11",
        "",
        f"**Correlation ID:** {correlation_id}",
        f"**Readiness:** {result.readiness.value}",
        f"**Analysis Mode:** {result.analysis_mode}",
        "",
        "## Counts",
        "",
        f"- Verified items: {result.verified_count}",
        f"- Inferred items: {result.inferred_count}",
        f"- Gaps: {result.gap_count}",
        f"- Warnings: {result.warning_count}",
        f"- Suggestions: {result.suggestion_count}",
        "",
        "## No Mutation Applied",
        "",
        f"no_mutation_applied: {result.no_mutation_applied}",
        "No repository files were modified by this guidance run.",
        "",
    ]

    if result.next_best_action:
        lines += [
            "## Next Best Action",
            "",
            result.next_best_action,
            "",
        ]

    if result.items:
        lines += ["## Guidance Items", ""]
        for item in result.items:
            state_label = "[VERIFIED]" if item.state == GuidanceState.VERIFIED else "[inferred]"
            lines.append(
                f"- [{item.severity.value.upper()}] {state_label} {item.title} ({item.id})"
            )
        lines.append("")

    return "\n".join(lines)


def _safe_dirname(correlation_id: str) -> str:
    """Convert a correlation ID into a filesystem-safe directory name."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in correlation_id)
    return safe[:64] or "unknown"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
