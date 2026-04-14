"""Capability namespace proof emission — SDK-CLIENT-03 §11, §16.

Writes validation and creation artifacts to the tool-owned state directory
for advisory mode, ingestion filtering, and foreign-repo workflows.

§11 out-of-tree advisory layout:
  <state_dir>/capability_namespace/<request-id-or-session-ref>/
    validation.json
    accepted.json
    rejected.json
    summary.md

§16: proof must include validated identifier, reject reasons, no-write
     statement for foreign repos, and creation timestamp.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from keyhole_sdk.capability.namespace import (
    CapabilityValidationResult,
    NamespaceRejectReason,
)


def _safe_dir_name(raw: str, max_len: int = 64) -> str:
    """Filesystem-safe directory name — alphanumeric and hyphens only."""
    if not raw:
        return "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)
    return safe[:max_len] or "unknown"


def emit_namespace_proof(
    state_dir: str | Path,
    result: CapabilityValidationResult,
    *,
    session_ref: str = "",
    write_mode: bool = False,
    artifact_path: str = "",
) -> Path:
    """Write namespace validation artifacts to the tool-owned state dir.

    §11: layout is <state_dir>/capability_namespace/<safe-session-ref>/.
    §16: proof includes validated identifier, reasons, and no-write note.

    Returns the directory path that was written.
    """
    safe_ref = _safe_dir_name(session_ref or result.name or "unknown")
    out_dir = Path(state_dir) / "capability_namespace" / safe_ref
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    # validation.json — full result
    validation = result.to_dict()
    validation["emitted_at"] = now
    validation["write_mode"] = write_mode
    if artifact_path:
        validation["artifact_path"] = artifact_path
    (out_dir / "validation.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )

    # accepted.json / rejected.json — filtering surfaces for ingestion
    if result.valid:
        (out_dir / "accepted.json").write_text(
            json.dumps({"names": [result.name], "emitted_at": now}, indent=2),
            encoding="utf-8",
        )
        (out_dir / "rejected.json").write_text(
            json.dumps({"names": [], "emitted_at": now}, indent=2),
            encoding="utf-8",
        )
    else:
        (out_dir / "accepted.json").write_text(
            json.dumps({"names": [], "emitted_at": now}, indent=2),
            encoding="utf-8",
        )
        (out_dir / "rejected.json").write_text(
            json.dumps(
                {
                    "names": [result.name],
                    "reject_reasons": [r.value for r in result.reject_reasons],
                    "emitted_at": now,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # summary.md
    summary = _build_summary_md(result, write_mode=write_mode, artifact_path=artifact_path, now=now)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")

    return out_dir


def emit_namespace_batch_proof(
    state_dir: str | Path,
    results: List[CapabilityValidationResult],
    *,
    session_ref: str = "",
) -> Path:
    """Write batch namespace validation artifacts (e.g. from ingestion filtering).

    §11: layout is <state_dir>/capability_namespace/<safe-session-ref>/.
    Produces accepted.json, rejected.json, and summary.md for the batch.
    """
    safe_ref = _safe_dir_name(session_ref or "batch")
    out_dir = Path(state_dir) / "capability_namespace" / safe_ref
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    accepted = [r.name for r in results if r.valid]
    rejected = [
        {"name": r.name, "reasons": [x.value for x in r.reject_reasons]}
        for r in results
        if not r.valid
    ]

    (out_dir / "accepted.json").write_text(
        json.dumps({"names": accepted, "emitted_at": now}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "rejected.json").write_text(
        json.dumps({"entries": rejected, "emitted_at": now}, indent=2),
        encoding="utf-8",
    )

    # validation.json — full list
    (out_dir / "validation.json").write_text(
        json.dumps(
            {
                "total": len(results),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "results": [r.to_dict() for r in results],
                "emitted_at": now,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Capability Namespace Batch Validation",
        "",
        f"**Total examined:** {len(results)}",
        f"**Accepted:** {len(accepted)}",
        f"**Rejected:** {len(rejected)}",
        "",
    ]
    if accepted:
        lines.append("## Accepted")
        for n in accepted:
            lines.append(f"  - `{n}`")
        lines.append("")
    if rejected:
        lines.append("## Rejected")
        for entry in rejected:
            lines.append(f"  - `{entry['name']}`: {', '.join(entry['reasons'])}")
        lines.append("")
    lines.append(f"*Emitted: {now}*")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    return out_dir


# ── Private ───────────────────────────────────────────────────

def _build_summary_md(
    result: CapabilityValidationResult,
    *,
    write_mode: bool,
    artifact_path: str,
    now: str,
) -> str:
    status = "✓ Valid" if result.valid else "✗ Invalid"
    lines = [
        "# Capability Namespace Validation",
        "",
        f"**Name:** `{result.name}`",
        f"**Status:** {status}",
    ]
    if result.valid:
        lines.append(f"**Normalized:** `{result.normalized}`")
    else:
        lines.append("")
        lines.append("## Validation Issues")
        for r in result.reject_reasons:
            lines.append(f"  - `{r.value}`")
        if result.suggestion:
            lines.append("")
            lines.append(f"**Suggestion:** `{result.suggestion}`")
        lines.append("")
        lines.append("## Expected Format")
        lines.append("```")
        lines.append("<domain>.<category>.<capability>.v<major>")
        lines.append("```")
        lines.append("Example: `payment.stripe.integration.v1`")

    if write_mode and artifact_path:
        lines.append("")
        lines.append(f"**Written to:** `{artifact_path}`")
    elif not write_mode:
        lines.append("")
        lines.append(
            "> Advisory mode — no in-repo artifacts were written. "
            "This output is out-of-tree only."
        )

    lines.append("")
    lines.append(f"*Emitted: {now}*")
    return "\n".join(lines)
