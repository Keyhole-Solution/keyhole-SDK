"""Memory boundary proof emission — SDK-CLIENT-18.

Writes enforcement proof to a tool-owned local state directory.

Proof shape:
  <state_dir>/memory_boundary/
    attempted-surface.json   — what was attempted and when
    rejection.json           — error class, reason, lawful alternatives
    summary.md               — human-readable summary
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def emit_memory_boundary_proof(
    state_dir: str | Path,
    attempted_surface: str,
    rejection_reason: str,
    correlation_id: Optional[str] = None,
) -> dict:
    """Emit memory boundary enforcement proof to the local state directory.

    Creates three artifacts:
      * attempted-surface.json — records what surface was attempted
      * rejection.json         — records error class, reason, lawful alternatives
      * summary.md             — human-readable enforcement summary

    Parameters
    ----------
    state_dir:
        Root directory for tool-owned state (e.g. ~/.keyhole or a tmp path).
    attempted_surface:
        Description of the surface the caller tried to access.
    rejection_reason:
        Short description of why the attempt was rejected.
    correlation_id:
        Optional correlation ID; generated if omitted.

    Returns
    -------
    dict with keys: attempted_surface_path, rejection_path, summary_path,
    correlation_id.
    """
    corr = correlation_id or str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()

    boundary_dir = Path(state_dir) / "memory_boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    # ── attempted-surface.json ────────────────────────────────────────────────
    attempted_path = boundary_dir / "attempted-surface.json"
    attempted_data = {
        "attempted_surface": attempted_surface,
        "correlation_id": corr,
        "timestamp": ts,
        "story": "SDK-CLIENT-18",
    }
    attempted_path.write_text(json.dumps(attempted_data, indent=2), encoding="utf-8")

    # ── rejection.json ────────────────────────────────────────────────────────
    rejection_path = boundary_dir / "rejection.json"
    rejection_data = {
        "error_class": "DirectMemoryAccessNotAllowed",
        "rejection_reason": rejection_reason,
        "boundary_explanation": (
            "Memory is governed through context, run, proof, and explainability surfaces. "
            "The public SDK does not expose direct canonical memory access."
        ),
        "lawful_alternatives": [
            "keyhole context compile",
            "keyhole context inspect",
            "keyhole run --context <digest>",
            "keyhole runs status <run-id>",
        ],
        "correlation_id": corr,
        "timestamp": ts,
    }
    rejection_path.write_text(json.dumps(rejection_data, indent=2), encoding="utf-8")

    # ── summary.md ────────────────────────────────────────────────────────────
    summary_path = boundary_dir / "summary.md"
    summary_lines = [
        "# Memory Boundary Enforcement — SDK-CLIENT-18",
        "",
        f"**Correlation ID:** {corr}",
        f"**Timestamp:** {ts}",
        "",
        "## Attempted Surface",
        "",
        f"`{attempted_surface or '(none)'}`",
        "",
        "## Rejection",
        "",
        rejection_reason,
        "",
        "## Lawful Alternatives",
        "",
        "- `keyhole context compile`",
        "- `keyhole context inspect`",
        "- `keyhole run --context <digest>`",
        "- `keyhole runs status <run-id>`",
        "",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "attempted_surface_path": str(attempted_path),
        "rejection_path": str(rejection_path),
        "summary_path": str(summary_path),
        "correlation_id": corr,
    }
