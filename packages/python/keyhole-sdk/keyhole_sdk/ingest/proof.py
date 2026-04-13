"""Ingestion proof emitter — SDK-CLIENT-10 §17.

Writes proof artifacts for ingestion attempts. By default, proof
lives out-of-tree in tool-owned state — NOT inside the target repo
(which is likely foreign and non-Keyhole).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def emit_ingestion_proof(
    *,
    state_dir: Path,
    correlation_id: str,
    request_dict: Dict[str, Any],
    package_manifest: Dict[str, Any],
    outcome_dict: Dict[str, Any],
) -> Path:
    """Write proof artifacts for an ingestion attempt (§17).

    Proof is written for both success and failure.
    Default location: <state_dir>/ingest/<correlation_id>/

    Args:
        state_dir: Tool-owned state directory (e.g. ~/.keyhole/state).
        correlation_id: Correlation ID for this ingestion attempt.
        request_dict: Proof-safe request data.
        package_manifest: Package manifest summary.
        outcome_dict: Proof-safe outcome data.

    Returns:
        Path to the proof directory.
    """
    safe_id = _safe_dirname(correlation_id)
    proof_dir = state_dir / "ingest" / safe_id
    proof_dir.mkdir(parents=True, exist_ok=True)

    # request.json
    _write_json(proof_dir / "request.json", request_dict)

    # package_manifest.json
    _write_json(proof_dir / "package_manifest.json", package_manifest)

    # response.json
    _write_json(proof_dir / "response.json", outcome_dict)

    # correlation.json
    correlation_data: Dict[str, Any] = {
        "correlation_id": correlation_id,
        "proof_written_at": datetime.now(timezone.utc).isoformat(),
        "request_summary": {
            k: v for k, v in request_dict.items()
            if k in ("repo_identity", "shadow", "correlation_id", "identity_fingerprint", "timestamp")
        } if isinstance(request_dict, dict) else {},
    }
    _write_json(proof_dir / "correlation.json", correlation_data)

    # summary.md
    summary = _render_summary(
        correlation_id=correlation_id,
        request_dict=request_dict,
        outcome_dict=outcome_dict,
    )
    (proof_dir / "summary.md").write_text(summary, encoding="utf-8")

    return proof_dir


def _render_summary(
    *,
    correlation_id: str,
    request_dict: Dict[str, Any],
    outcome_dict: Dict[str, Any],
) -> str:
    """Render a human-readable summary.md for ingestion proof."""
    pkg_summary = request_dict.get("package_summary", request_dict)
    repo_identity = pkg_summary.get("repo_identity", "unknown")
    shadow = pkg_summary.get("shadow", False)
    status = outcome_dict.get("status", "unknown")
    compatibility = outcome_dict.get("compatibility", "unknown")
    mode = "SHADOW" if shadow else "GOVERNED"

    lines = [
        f"# Ingestion Proof — {correlation_id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Repo | `{repo_identity}` |",
        f"| Mode | {mode} |",
        f"| Status | {status} |",
        f"| Compatibility | {compatibility} |",
        f"| Correlation ID | `{correlation_id}` |",
    ]

    if outcome_dict.get("ingestion_id"):
        lines.append(f"| Ingestion ID | `{outcome_dict['ingestion_id']}` |")

    if outcome_dict.get("graph_summary"):
        gs = outcome_dict["graph_summary"]
        lines.append(f"| Graph Nodes | {gs.get('node_count', 0)} |")
        lines.append(f"| Graph Edges | {gs.get('edge_count', 0)} |")

    inferred = outcome_dict.get("inferred_capabilities", [])
    if inferred:
        lines.append(f"| Inferred Capabilities | {len(inferred)} |")

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

    if outcome_dict.get("suggested_actions"):
        lines.append("")
        lines.append("## Suggested Next Actions")
        lines.append("")
        for a in outcome_dict["suggested_actions"]:
            lines.append(f"- {a}")

    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write a JSON file."""
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _safe_dirname(value: str) -> str:
    """Sanitize a string for use as a directory name."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in value)
    return safe or "unknown"
