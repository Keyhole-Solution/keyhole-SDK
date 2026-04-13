"""Registration proof emitter — SDK-CLIENT-07 §15, §16.

Writes proof artifacts for registration attempts. By default, proof
lives out-of-tree in tool-owned state — NOT inside the target repo
(which may be foreign and non-Keyhole).

Proof is emitted for every registration attempt: success, replayed,
accepted, deferred, and rejected.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def emit_registration_proof(
    *,
    state_dir: Path,
    correlation_id: str,
    request_dict: Dict[str, Any],
    artifacts_snapshot: Dict[str, Any],
    outcome_dict: Dict[str, Any],
    identity_context: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write proof artifacts for a registration attempt (§15).

    Proof is written for both success and failure.
    Default location: <state_dir>/repo_register/<correlation_id>/

    Args:
        state_dir: Tool-owned state directory (e.g. ~/.keyhole/state).
        correlation_id: Correlation ID for this registration attempt.
        request_dict: Proof-safe request data.
        artifacts_snapshot: Deterministic snapshot of registration inputs.
        outcome_dict: Proof-safe outcome data.
        identity_context: Resolved identity binding, if available.

    Returns:
        Path to the proof directory.
    """
    safe_id = _safe_dirname(correlation_id)
    proof_dir = state_dir / "repo_register" / safe_id
    proof_dir.mkdir(parents=True, exist_ok=True)

    # request.json
    _write_json(proof_dir / "request.json", request_dict)

    # artifacts_snapshot.json (§16)
    _write_json(proof_dir / "artifacts_snapshot.json", artifacts_snapshot)

    # response.json
    _write_json(proof_dir / "response.json", outcome_dict)

    # identity_context.json (§11)
    if identity_context:
        _write_json(proof_dir / "identity_context.json", identity_context)

    # correlation.json
    correlation_data: Dict[str, Any] = {
        "correlation_id": correlation_id,
        "proof_written_at": datetime.now(timezone.utc).isoformat(),
        "request_summary": {
            k: v for k, v in request_dict.items()
            if k in (
                "payload_summary", "identity_fingerprint", "timestamp",
            )
        } if isinstance(request_dict, dict) else {},
    }
    _write_json(proof_dir / "correlation.json", correlation_data)

    # summary.md
    summary = _render_summary(
        correlation_id=correlation_id,
        request_dict=request_dict,
        outcome_dict=outcome_dict,
        identity_context=identity_context,
    )
    (proof_dir / "summary.md").write_text(summary, encoding="utf-8")

    # digest.txt — correlation reference
    (proof_dir / "digest.txt").write_text(
        f"{correlation_id}\n", encoding="utf-8",
    )

    return proof_dir


from typing import Optional  # noqa: E402 (already imported but needed for function sig)


def _render_summary(
    *,
    correlation_id: str,
    request_dict: Dict[str, Any],
    outcome_dict: Dict[str, Any],
    identity_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a human-readable summary.md for registration proof."""
    payload_summary = request_dict.get("payload_summary", request_dict)
    repo_name = payload_summary.get("repo_name", "unknown")
    source = payload_summary.get("registration_source", "unknown")
    shadow = payload_summary.get("shadow", False)
    status = outcome_dict.get("status", "unknown")
    readiness = payload_summary.get("readiness", "unknown")
    is_replay = outcome_dict.get("is_replay", False)
    mode = "SHADOW" if shadow else "GOVERNED"

    lines = [
        f"# Registration Proof — {correlation_id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Repo | `{repo_name}` |",
        f"| Source | {source} |",
        f"| Mode | {mode} |",
        f"| Status | {status} |",
        f"| Readiness | {readiness} |",
        f"| Replay | {is_replay} |",
        f"| Correlation ID | `{correlation_id}` |",
    ]

    if outcome_dict.get("registration_id"):
        lines.append(f"| Registration ID | `{outcome_dict['registration_id']}` |")

    # Identity binding
    binding = outcome_dict.get("identity_binding") or identity_context
    if binding and isinstance(binding, dict):
        lines.append("")
        lines.append("## Identity Binding")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        for k, v in binding.items():
            if v:
                lines.append(f"| {k} | `{v}` |")

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
