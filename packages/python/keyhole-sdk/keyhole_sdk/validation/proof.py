"""Validation proof emission — SDK-CLIENT-04 §14.

Writes a deterministic, human-readable proof artifact to state_dir.

Layout:
    <state_dir>/validation/<session_ref>/
        validation_result.json      — full structured result
        validation_summary.md       — human-readable summary
        normalization_preview.json  — dependency normalization preview
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from keyhole_sdk.validation.models import ValidationResult, ValidationStatus


def emit_validation_proof(
    state_dir: Union[str, Path],
    result: ValidationResult,
    *,
    session_ref: str = "",
) -> Path:
    """Write validation proof artifacts to *state_dir*.

    Returns the Path of the directory containing the emitted artifacts.

    §14 guarantees:
    - Deterministic layout under <state_dir>/validation/<session_ref>/
    - JSON artifacts are valid and fully serialisable.
    - Markdown summary is human-readable without additional tooling.
    - session_ref is sanitised to a filesystem-safe name.
    """
    safe_ref = _safe_dir_name(session_ref or result.repo or "unknown")
    out_dir = Path(state_dir) / "validation" / safe_ref
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    # ── validation_result.json ─────────────────────────────────────────────
    full = result.to_dict()
    full["emitted_at"] = now
    (out_dir / "validation_result.json").write_text(
        json.dumps(full, indent=2), encoding="utf-8"
    )

    # ── normalization_preview.json ─────────────────────────────────────────
    (out_dir / "normalization_preview.json").write_text(
        json.dumps(result.normalization_preview.to_dict(), indent=2), encoding="utf-8"
    )

    # ── validation_summary.md ─────────────────────────────────────────────
    (out_dir / "validation_summary.md").write_text(
        _build_summary_md(result, now), encoding="utf-8"
    )

    return out_dir


# ── Internal helpers ──────────────────────────────────────────────────────────

def _safe_dir_name(raw: str, max_len: int = 64) -> str:
    """Return a filesystem-safe directory name from an arbitrary string."""
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw)
    return safe[:max_len] or "unknown"


def _build_summary_md(result: ValidationResult, emitted_at: str) -> str:
    """Build the human-readable validation summary document."""
    lines = [
        f"# Keyhole Validation Summary",
        f"",
        f"| Field        | Value                    |",
        f"|:-------------|:-------------------------|",
        f"| Repo         | `{result.repo or '—'}`   |",
        f"| Status       | **{result.status.value}**|",
        f"| Posture      | {result.repo_posture.value} |",
        f"| Readiness    | {result.readiness.value} |",
        f"| Mode         | {result.mode}            |",
        f"| Emitted at   | {emitted_at}             |",
        f"",
    ]

    # Files table
    if result.files:
        lines += [
            "## File Results",
            "",
            "| File | Status |",
            "|:-----|:-------|",
        ]
        for fname, status in sorted(result.files.items()):
            lines.append(f"| `{fname}` | {status} |")
        lines.append("")

    # Issues
    if result.issues:
        lines += [
            "## Issues",
            "",
        ]
        for issue in result.issues:
            location = f"`{issue.file}`"
            if issue.field:
                location += f" › `{issue.field}`"
            lines.append(f"### {location}")
            lines.append(f"")
            lines.append(f"**Reason:** {issue.reason}")
            if issue.repair:
                lines.append(f"")
                lines.append(f"**Repair:**")
                for step in issue.repair:
                    lines.append(f"- {step}")
            lines.append(f"")
    else:
        status_label = result.status.value
        if status_label == ValidationStatus.PASS:
            lines.append("_No issues found._")
        elif status_label == ValidationStatus.WARN:
            lines.append("_Advisory warnings only — no blocking issues._")
        lines.append("")

    # Normalization preview
    deps = result.normalization_preview.dependencies
    if deps:
        lines += [
            "## Normalization Preview",
            "",
            "| Capability | Provider | Digest |",
            "|:-----------|:---------|:-------|",
        ]
        for dep in deps:
            cap = dep.get("capability", "—")
            prov = dep.get("provider") or "—"
            digest = dep.get("digest") or "—"
            lines.append(f"| `{cap}` | {prov} | `{digest}` |")
        lines.append("")

    return "\n".join(lines)
