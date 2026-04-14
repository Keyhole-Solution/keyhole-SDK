"""Passport proof emission — SDK-CLIENT-05 §18.

Writes a deterministic, human-readable proof artifact to tool-owned state_dir.

Layout:
    <state_dir>/passport/<session_ref>/
        generation_result.json   — full structured result
        summary.md               — human-readable summary (§16 UX)
        digest.txt               — bare digest string
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from keyhole_sdk.passport.models import PassportGenerationResult, PassportStatus


def emit_passport_proof(
    state_dir: Union[str, Path],
    result: PassportGenerationResult,
    *,
    session_ref: str = "",
) -> Path:
    """Write passport generation proof artifacts to *state_dir*.

    §18: Required proof metadata includes passport digest, source files used,
    capability count, generation result, and repo posture.

    Returns the path of the directory containing the emitted artifacts.
    """
    safe_ref = _safe_dir_name(session_ref or result.repo or "unknown")
    out_dir = Path(state_dir) / "passport" / safe_ref
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    # ── generation_result.json ────────────────────────────────────────────
    full = result.to_dict()
    full["emitted_at"] = now
    (out_dir / "generation_result.json").write_text(
        json.dumps(full, indent=2), encoding="utf-8"
    )

    # ── digest.txt ────────────────────────────────────────────────────────
    (out_dir / "digest.txt").write_text(result.digest or "", encoding="utf-8")

    # ── summary.md ────────────────────────────────────────────────────────
    (out_dir / "summary.md").write_text(
        _build_summary_md(result, now), encoding="utf-8"
    )

    return out_dir


# ── Internal helpers ──────────────────────────────────────────────────────────

def _safe_dir_name(raw: str, max_len: int = 64) -> str:
    """Return a filesystem-safe directory name."""
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw)
    return safe[:max_len] or "unknown"


def _build_summary_md(result: PassportGenerationResult, emitted_at: str) -> str:
    """Build the §16 human-readable summary document."""
    lines = [
        "# Capability Passport Generation Summary",
        "",
        "| Field            | Value                        |",
        "|:-----------------|:-----------------------------|",
        f"| Repo             | `{result.repo or '—'}`       |",
        f"| Status           | **{result.status.value}**    |",
        f"| Readiness        | {result.readiness.value}     |",
        f"| Capabilities     | {result.capability_count}    |",
        f"| Digest           | `{result.digest or '—'}`     |",
        f"| Artifact path    | `{result.artifact_path or '—'}`|",
        f"| Emitted at       | {emitted_at}                 |",
        "",
    ]

    if result.source_files:
        lines += [
            "## Source Files",
            "",
        ]
        for sf in result.source_files:
            lines.append(f"- `{sf}`")
        lines.append("")

    if result.artifact and result.artifact.capabilities:
        lines += [
            "## Declared Capabilities",
            "",
            "| Name | Visibility | Status |",
            "|:-----|:-----------|:-------|",
        ]
        for cap in result.artifact.capabilities:
            lines.append(f"| `{cap.name}` | {cap.visibility} | {cap.status} |")
        lines.append("")

    if result.issues:
        lines += [
            "## Issues",
            "",
        ]
        for issue in result.issues:
            location = f"`{issue.file}`" if issue.file else "(general)"
            if issue.field:
                location += f" › `{issue.field}`"
            lines.append(f"### {location}")
            lines.append("")
            lines.append(f"**Reason:** {issue.reason}")
            if issue.repair:
                lines.append("")
                lines.append("**Repair:**")
                for step in issue.repair:
                    lines.append(f"- {step}")
            lines.append("")

    if result.status == PassportStatus.GENERATED:
        lines += [
            "## Next Steps",
            "",
            "- The passport is ready for later boundary verification.",
            "- Run: `keyhole register` — when ready to register with the MCP boundary.",
            "",
        ]
    else:
        lines += [
            "## Next Steps",
            "",
            "- Review the issues above and run `keyhole validate` for full diagnostics.",
            "- Run `keyhole passport generate` again after fixing issues.",
            "",
        ]

    return "\n".join(lines)
