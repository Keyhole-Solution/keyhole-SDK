"""Budget/limit proof emission — SDK-CLIENT-19 §14.

Writes proof artifacts to a tool-owned local state path.

§14.4 default artifact location:
  <tool-owned-state>/
    runs/
      <run-id-or-request-id>/
        request.json       — BudgetPressureRequest fields
        latest-status.json — run status at proof time
        outcome.json       — full LimitResult proof dict
        budget.json        — budget snapshots extracted for quick inspection
        summary.md         — human-readable summary

§14.1: Budget/limit data must be preserved even on failure, defer,
partial execution, and resumed observation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from keyhole_sdk.budget.models import BudgetPressureRequest, LimitResult
from keyhole_sdk.budget.renderer import render_budget_summary


def emit_budget_proof(
    state_dir: Path,
    run_id: str,
    result: LimitResult,
    request: Optional[BudgetPressureRequest] = None,
) -> Path:
    """Write budget/limit proof artifacts to a tool-owned state path.

    Returns the proof directory created.

    §14.1: Proof is emitted for any outcome — including pressure and error.
    §14.4: Default artifact location is tool-owned state, never in-repo
    by default (because not every repo is Keyhole-native).
    """
    # Safe directory name: use run_id or request_id, sanitized
    safe_id = _safe_dir_name(run_id or (request.run_id if request else "") or "unknown")
    proof_dir = state_dir / "runs" / safe_id
    proof_dir.mkdir(parents=True, exist_ok=True)

    # ── outcome.json — full proof dict (§14.2) ────────────────────────────
    outcome_data = result.to_proof_dict()
    _write_json(proof_dir / "outcome.json", outcome_data)

    # ── budget.json — budget snapshots for quick inspection ───────────────
    budget_data = {
        "run_id": result.run_id,
        "limit_outcome": result.outcome_class.value,
        "limit_class": result.limit_class,
        "budget_snapshots": [s.to_dict() for s in result.budget_snapshots],
        "retry_after": result.retry_after,
        "retry_safe": result.retry_safe,
        "partial_execution": result.partial_execution,
    }
    _write_json(proof_dir / "budget.json", budget_data)

    # ── latest-status.json ────────────────────────────────────────────────
    status_data = {
        "run_id": result.run_id,
        "status": result.status,
        "is_terminal": result.is_terminal,
        "parsed_at": result.parsed_at,
    }
    _write_json(proof_dir / "latest-status.json", status_data)

    # ── request.json — BudgetPressureRequest (if available) ──────────────
    if request is not None:
        request_data = {
            "run_id": request.run_id,
            "request_id": request.request_id,
            "correlation_id": request.correlation_id,
            "mcp_url": request.mcp_url,
            "queried_at": request.queried_at,
        }
        _write_json(proof_dir / "request.json", request_data)

    # ── summary.md — human-readable (§14.3) ──────────────────────────────
    summary_lines = [
        "# Budget and Limit Proof\n",
        render_budget_summary(result),
        "",
        "## Platform Lawfulness",
        "The platform remained governed under pressure." if result.is_pressure()
        else "No pressure conditions were present.",
        "",
    ]
    if result.repair_guidance:
        summary_lines.append("## Next Steps")
        for step in result.repair_guidance:
            summary_lines.append(f"- {step}")
        summary_lines.append("")

    (proof_dir / "summary.md").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )

    return proof_dir


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _safe_dir_name(raw: str, max_len: int = 64) -> str:
    """Sanitize a raw ID into a safe directory name."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw)
    return safe[:max_len] or "unknown"
