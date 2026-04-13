"""Context proof artifacts — SDK-CLIENT-16 §15.

Writes proof artifacts for context lifecycle activity into the
canonical scaffold created by SDK-CLIENT-02:

    proof_bundle/
      core/
        context/
          <ctxpack_digest>/
            compile-request.json
            compile-response.json
            summary.md
      extended/
        context/
          <ctxpack_digest>/
            inspect-output.json
            debug.json

Also adds context-binding.json to run proof directories.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.context_lifecycle.compile import ContextCompileRequest, ContextCompileResult


def emit_context_proof(
    *,
    repo_dir: Path,
    request: ContextCompileRequest,
    result: ContextCompileResult,
) -> Path:
    """Write proof artifacts for a context compile invocation.

    Returns the path to the core proof directory.
    Proof is emitted even on failure (§15).
    """
    safe_digest = _safe_dirname(
        result.ctxpack_digest or result.correlation_id or "unknown"
    )

    core_dir = repo_dir / "proof_bundle" / "core" / "context" / safe_digest
    extended_dir = repo_dir / "proof_bundle" / "extended" / "context" / safe_digest

    core_dir.mkdir(parents=True, exist_ok=True)
    extended_dir.mkdir(parents=True, exist_ok=True)

    # ── core/context/<digest>/compile-request.json ──
    _write_json(core_dir / "compile-request.json", request.to_proof_dict())

    # ── core/context/<digest>/compile-response.json ──
    response_proof: Dict[str, Any] = {
        "success": result.success,
        "ctxpack_digest": result.ctxpack_digest,
        "http_status": result.http_status,
        "correlation_id": result.correlation_id,
    }
    if result.error_class:
        response_proof["error_class"] = result.error_class
    if result.reason:
        response_proof["reason"] = result.reason
    if result.metadata:
        response_proof["metadata"] = result.metadata
    _write_json(core_dir / "compile-response.json", response_proof)

    # ── core/context/<digest>/summary.md ──
    summary = _render_compile_summary(request, result)
    (core_dir / "summary.md").write_text(summary, encoding="utf-8")

    # ── extended/context/<digest>/debug.json ──
    debug_data: Dict[str, Any] = {
        "proof_written_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": result.correlation_id,
        "repo": request.repo_name,
    }
    if result.proof:
        debug_data["transport_proof"] = result.proof.to_dict()
    _write_json(extended_dir / "debug.json", debug_data)

    return core_dir


def emit_inspect_proof(
    *,
    repo_dir: Path,
    ctxpack_digest: str,
    inspect_data: Dict[str, Any],
) -> Path:
    """Write proof artifacts for a context inspect invocation.

    Returns the extended proof directory.
    """
    safe_digest = _safe_dirname(ctxpack_digest or "unknown")
    extended_dir = repo_dir / "proof_bundle" / "extended" / "context" / safe_digest
    extended_dir.mkdir(parents=True, exist_ok=True)

    _write_json(extended_dir / "inspect-output.json", inspect_data)

    return extended_dir


def emit_context_binding_proof(
    *,
    repo_dir: Path,
    correlation_id: str,
    ctxpack_digest: str,
    run_type: str,
    shadow: bool = False,
    auto_compiled: bool = False,
) -> Path:
    """Write context-binding.json into a run proof directory.

    §15: Run proof must include the bound ctxpack_digest.
    §15: --context auto must record the compile → bind transition.
    """
    safe_id = _safe_dirname(correlation_id)
    core_run_dir = repo_dir / "proof_bundle" / "core" / "runs" / safe_id
    core_run_dir.mkdir(parents=True, exist_ok=True)

    binding: Dict[str, Any] = {
        "ctxpack_digest": ctxpack_digest,
        "run_type": run_type,
        "correlation_id": correlation_id,
        "shadow": shadow,
        "auto_compiled": auto_compiled,
        "bound_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(core_run_dir / "context-binding.json", binding)

    return core_run_dir


def _render_compile_summary(
    request: ContextCompileRequest,
    result: ContextCompileResult,
) -> str:
    """Render a human-readable summary for the proof bundle."""
    status = "SUCCESS" if result.success else "FAILED"
    lines = [
        f"# Context Compile Proof — {result.ctxpack_digest or '(none)'}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Status | {status} |",
        f"| Repo | `{request.repo_name}` |",
        f"| Digest | `{result.ctxpack_digest or '(none)'}` |",
        f"| Correlation ID | `{result.correlation_id}` |",
        f"| Timestamp | {request.timestamp} |",
        f"| HTTP Status | {result.http_status} |",
    ]
    if result.summary:
        lines.append(f"| Summary | {result.summary} |")
    if result.error_class:
        lines.append(f"| Error Class | {result.error_class} |")
    if result.reason:
        lines.append(f"| Reason | {result.reason} |")
    if result.repair_guidance:
        lines.append("")
        lines.append("## Repair Guidance")
        lines.append("")
        for g in result.repair_guidance:
            lines.append(f"- {g}")

    lines.append("")
    if result.success and result.ctxpack_digest:
        lines.append("## Next Steps")
        lines.append("")
        lines.append(f"- Inspect: `keyhole context inspect --digest {result.ctxpack_digest}`")
        lines.append(f"- Run: `keyhole run --context {result.ctxpack_digest} --run-type <type>`")
        lines.append("")

    return "\n".join(lines)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write a JSON file."""
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _safe_dirname(name: str) -> str:
    """Sanitize a string for use as a directory name."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe or "unknown"
