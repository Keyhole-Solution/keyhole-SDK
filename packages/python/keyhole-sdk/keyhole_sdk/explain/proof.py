"""Explain proof emission — SDK-CLIENT-20 §14.

Writes governed artifacts to the state directory for
post-run inspection, audit, and support escalation.

§14.1 explain artifacts:
  <state_dir>/explain/<safe-id>/
    response.json     # explanation.to_proof_dict()
    rendered.md       # human-readable rendered explanation

§14.2 support-bundle artifacts:
  <state_dir>/support_bundle/<safe-id>/
    summary.md
    request.json
    run.json
    context.json
    events.json
    proof_refs.json
    outcome.json
    repair.json
    metadata.json
"""

from __future__ import annotations

import json
from pathlib import Path

from keyhole_sdk.explain.models import RunExplanation, SupportBundle
from keyhole_sdk.explain.renderer import render_explanation


def _safe_dir_name(raw: str | None, max_len: int = 64) -> str:
    """Convert an ID to a filesystem-safe directory name.

    Allows alphanumeric characters, hyphens, and underscores only.
    Replaces all other characters (including dots and slashes) with underscores
    to prevent path traversal via '..' components.
    """
    if not raw:
        return "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)
    return safe[:max_len] or "unknown"


def emit_explain_proof(
    state_dir: str | Path,
    run_id: str,
    explanation: RunExplanation,
) -> Path:
    """Write explain artifacts to <state_dir>/explain/<safe-id>/.

    Returns the explain directory path.

    §14.1: Always writes response.json + rendered.md.
    §10: Never writes tokens, credentials, or private keys.
    """
    safe_id = _safe_dir_name(run_id or explanation.run_id)
    explain_dir = Path(state_dir) / "explain" / safe_id
    explain_dir.mkdir(parents=True, exist_ok=True)

    proof = explanation.to_proof_dict()
    (explain_dir / "response.json").write_text(
        json.dumps(proof, indent=2, default=str),
        encoding="utf-8",
    )

    rendered = render_explanation(explanation)
    (explain_dir / "rendered.md").write_text(rendered, encoding="utf-8")

    return explain_dir


def emit_bundle_proof(
    state_dir: str | Path,
    run_id_or_request_id: str,
    bundle: SupportBundle,
) -> Path:
    """Write all support bundle files to <state_dir>/support_bundle/<safe-id>/.

    Each section from bundle.to_files_dict() is written as its own file.
    Missing sections get explicit omission files (§10 — never silent).

    Returns the bundle directory path.
    """
    safe_id = _safe_dir_name(
        run_id_or_request_id or bundle.run_id or bundle.request_id
    )
    bundle_dir = Path(state_dir) / "support_bundle" / safe_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    files = bundle.to_files_dict()
    for filename, content in files.items():
        target = bundle_dir / filename
        if filename.endswith(".md"):
            target.write_text(
                content if isinstance(content, str) else str(content),
                encoding="utf-8",
            )
        else:
            target.write_text(
                json.dumps(content, indent=2, default=str),
                encoding="utf-8",
            )

    return bundle_dir
