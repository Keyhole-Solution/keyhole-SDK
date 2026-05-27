"""`keyhole run` — governed run dispatch command.

SDK-CLIENT-09: First governed runtime participation surface.
SDK-CLIENT-16: Context lifecycle binding and no-floating-run enforcement.

Dispatches a governed run request through the MCP boundary using
the SDK-CLIENT-15 transport layer. Supports shadow mode, preflight
validation, proof emission, and deterministic repair guidance.

§11 (SDK-CLIENT-16): Governed runs must not proceed without explicit context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.context_lifecycle.compile import (
    build_compile_request,
    compile_context,
)
from keyhole_sdk.context_lifecycle.digest import is_auto, validate_digest
from keyhole_sdk.context_lifecycle.preflight import ContextPreflight
from keyhole_sdk.context_lifecycle.proof import emit_context_binding_proof, emit_context_proof
from keyhole_sdk.context_lifecycle.tracker import LocalContextTracker
from keyhole_sdk.dispatch.preflight import DispatchPreflight
from keyhole_sdk.run_dispatch.dispatcher import (
    OutcomeStatus,
    RunOutcome,
    dispatch_run,
)
from keyhole_sdk.run_dispatch.preflight import RunPreflight, PreflightFailure
from keyhole_sdk.run_dispatch.proof_emitter import emit_run_proof
from keyhole_sdk.run_dispatch.repair import map_repair_guidance
from keyhole_sdk.run_dispatch.request_builder import RunRequest, build_run_request
from keyhole_sdk.run_lifecycle.record import LocalRunRecordStore, RunRecord
from keyhole_sdk.run_lifecycle.proof import emit_accepted_proof
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    CommandResult,
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
)
from keyhole_sdk.config import DEFAULT_BASE_URL


def run_run(
    *,
    run_type: str = "context.compile",
    shadow: bool = False,
    context: str = "",
    input_file: str = "",
    output_path: str = "",
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole run`` or ``keyhole run --shadow``.

    Returns a CommandResult for the CLI to render.
    """
    repo_path = Path(repo_dir).resolve()
    command_label = "keyhole run --shadow" if shadow else "keyhole run"

    # ── Resolve credential store ──
    store_dir = Path(keyhole_home) if keyhole_home else None
    cred_store = CredentialStore(store_dir=store_dir)

    # ── Preflight ──
    preflight = RunPreflight(credential_store=cred_store)
    failure = preflight.check(repo_dir=repo_path, run_type=run_type)
    if failure is not None:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=failure.reason,
            data={
                "error_class": "PreflightFailure",
                "is_local": failure.is_local,
            },
            next_steps=failure.repair_guidance,
        )

    # ── SDK-CLIENT-16 §11: No-floating-run enforcement ──
    # Governed runs must not proceed without explicit context.
    if not context:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="Governed runs require explicit context. No --context provided.",
            data={
                "error_class": "missing_context",
                "is_local": True,
            },
            next_steps=[
                "Run: keyhole context compile — to compile context first.",
                "Then: keyhole run --context <digest> --run-type <type>",
                "Or: keyhole run --context auto --run-type <type>",
            ],
        )

    # ── Resolve repo name ──
    repo_name = preflight.load_repo_name(repo_path) or repo_path.name

    # ── Resolve identity ──
    session = cred_store.load()
    identity_fp = session.token_fingerprint if session else ""
    token = session.access_token if session else ""

    # ── SDK-CLIENT-16 §5.4: Resolve --context auto ──
    auto_compiled = False
    context_ref: Optional[str] = None

    if is_auto(context):
        # Auto-compile context, show the resulting digest, then bind
        auto_result = _auto_compile_context(
            repo_path=repo_path,
            repo_name=repo_name,
            identity_fp=identity_fp,
            token=token,
            mcp_url=mcp_url,
        )
        if auto_result is not None and not isinstance(auto_result, str):
            # auto_result is a CommandResult (failure)
            return auto_result
        if auto_result is None:
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_FAILURE,
                summary="--context auto: context compile failed.",
                data={"error_class": "auto_compile_failed", "is_local": False},
                next_steps=[
                    "Run: keyhole context compile — to debug.",
                    "Then: keyhole run --context <digest> --run-type <type>",
                ],
            )
        context_ref = auto_result
        auto_compiled = True
    else:
        # Validate explicit digest shape locally
        digest_error = validate_digest(context)
        if digest_error:
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_INVALID_INPUT,
                summary=digest_error,
                data={"error_class": "malformed_digest", "is_local": True},
                next_steps=[
                    "Provide a valid digest or use --context auto.",
                    "Run: keyhole context compile — to get a valid digest.",
                ],
            )
        context_ref = context

    # ── Resolve input data ──
    input_data: Optional[Dict[str, Any]] = None
    if input_file:
        input_path = Path(input_file)
        if not input_path.exists():
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_INVALID_INPUT,
                summary=f"Input file not found: {input_file}",
                next_steps=["Check the --input path and try again."],
            )
        try:
            input_data = json.loads(input_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_INVALID_INPUT,
                summary=f"Invalid input file: {exc}",
                next_steps=["Ensure --input file is valid JSON."],
            )

    # ── Build request ──
    correlation_id = generate_request_id()
    request = build_run_request(
        run_type=run_type,
        repo_name=repo_name,
        shadow=shadow,
        context_ref=context_ref,
        input_data=input_data,
        correlation_id=correlation_id,
        identity_fingerprint=identity_fp,
    )

    # ── Build transport ──
    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(
        base_url=mcp_url,
        auth_provider=auth_provider,
    )

    # ── Dispatch ──
    try:
        outcome = dispatch_run(transport=transport, request=request)
    finally:
        transport.close()

    # ── Emit proof ──
    proof_dir = _safe_emit_proof(
        repo_dir=repo_path,
        request=request,
        outcome=outcome,
        correlation_id=correlation_id,
    )

    # ── SDK-CLIENT-16 §15: Emit context-binding proof ──
    if context_ref:
        _safe_emit_context_binding(
            repo_dir=repo_path,
            correlation_id=correlation_id,
            ctxpack_digest=context_ref,
            run_type=run_type,
            shadow=shadow,
            auto_compiled=auto_compiled,
        )

    # ── SDK-CLIENT-17 §8/§9: Persist local run record for accepted/deferred ──
    if outcome.status in (OutcomeStatus.ACCEPTED, OutcomeStatus.DEFERRED):
        _safe_persist_run_record(
            repo_dir=repo_path,
            outcome=outcome,
            request=request,
            context_ref=context_ref,
            proof_dir=proof_dir,
        )

    # ── Render outcome ──
    return _outcome_to_result(
        outcome=outcome,
        command_label=command_label,
        proof_dir=proof_dir,
        ctxpack_digest=context_ref,
        auto_compiled=auto_compiled,
    )


def _safe_emit_proof(
    *,
    repo_dir: Path,
    request: RunRequest,
    outcome: RunOutcome,
    correlation_id: str,
) -> Optional[Path]:
    """Emit proof artifacts, returning None on I/O failure."""
    try:
        transport_proof = outcome.proof.to_dict() if outcome.proof else None
        return emit_run_proof(
            repo_dir=repo_dir,
            request=request,
            outcome_dict=outcome.to_proof_dict(),
            correlation_id=correlation_id,
            transport_proof_dict=transport_proof,
        )
    except OSError:
        return None


def _safe_emit_context_binding(
    *,
    repo_dir: Path,
    correlation_id: str,
    ctxpack_digest: str,
    run_type: str,
    shadow: bool,
    auto_compiled: bool,
) -> None:
    """Emit context-binding proof, swallowing I/O errors."""
    try:
        emit_context_binding_proof(
            repo_dir=repo_dir,
            correlation_id=correlation_id,
            ctxpack_digest=ctxpack_digest,
            run_type=run_type,
            shadow=shadow,
            auto_compiled=auto_compiled,
        )
    except OSError:
        pass


def _safe_persist_run_record(
    *,
    repo_dir: Path,
    outcome: RunOutcome,
    request: RunRequest,
    context_ref: Optional[str],
    proof_dir: Optional[Path],
) -> None:
    """Persist a local run record for accepted/deferred runs (SDK-CLIENT-17 §8)."""
    try:
        store = LocalRunRecordStore(repo_dir)
        record = RunRecord(
            request_id=getattr(outcome.proof, "request_id", "") if outcome.proof else "",
            run_id=outcome.run_id or "",
            command="keyhole run",
            mode="shadow" if outcome.shadow else "regular",
            run_type=outcome.run_type,
            ctxpack_digest=context_ref or "",
            submitted_at=request.timestamp,
            last_known_status=outcome.status.value,
            proof_path=str(proof_dir) if proof_dir else "",
            repo_name=outcome.repo_name,
            repo_path=str(repo_dir),
            correlation_id=outcome.correlation_id,
        )
        store.save(record)
    except (OSError, ValueError):
        pass

    # Also emit accepted-stage proof (SDK-CLIENT-17 §15)
    try:
        emit_accepted_proof(
            repo_dir=repo_dir,
            run_id=outcome.run_id or outcome.correlation_id,
            correlation_id=outcome.correlation_id,
            run_type=outcome.run_type,
            shadow=outcome.shadow,
            ctxpack_digest=context_ref or "",
            response_data=outcome.response_data,
        )
    except OSError:
        pass


def _auto_compile_context(
    *,
    repo_path: Path,
    repo_name: str,
    identity_fp: str,
    token: str,
    mcp_url: str,
) -> Optional[str | CommandResult]:
    """Auto-compile context and return the digest, or a failure CommandResult.

    §5.4: compile context automatically, show resulting digest, bind to it.
    Returns the digest string on success, or a CommandResult on failure,
    or None if compile returned no digest.
    """
    correlation_id = generate_request_id()
    request = build_compile_request(
        repo_name=repo_name,
        identity_fingerprint=identity_fp,
        correlation_id=correlation_id,
    )

    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(
        base_url=mcp_url,
        auth_provider=auth_provider,
    )

    try:
        result = compile_context(transport=transport, request=request)
    finally:
        transport.close()

    # Emit compile proof even during auto mode
    try:
        emit_context_proof(
            repo_dir=repo_path,
            request=request,
            result=result,
        )
    except OSError:
        pass

    # Track recent context
    if result.success and result.ctxpack_digest:
        try:
            tracker = LocalContextTracker(repo_path)
            tracker.save(
                ctxpack_digest=result.ctxpack_digest,
                repo_name=repo_name,
                correlation_id=correlation_id,
            )
        except OSError:
            pass
        return result.ctxpack_digest

    if not result.success:
        return CommandResult(
            command="keyhole run --context auto",
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"--context auto: compile failed: {result.reason[:120]}" if result.reason else "--context auto: compile failed.",
            data={
                "error_class": result.error_class or "auto_compile_failed",
                "reason": result.reason,
                "is_local": False,
            },
            next_steps=result.repair_guidance or [
                "Run: keyhole context compile — to debug.",
            ],
        )

    return None  # no digest returned


def _outcome_to_result(
    *,
    outcome: RunOutcome,
    command_label: str,
    proof_dir: Optional[Path],
    ctxpack_digest: Optional[str] = None,
    auto_compiled: bool = False,
) -> CommandResult:
    """Convert a RunOutcome to a CommandResult for CLI rendering."""
    proof_location = str(proof_dir) if proof_dir else "(proof not written)"

    if outcome.status == OutcomeStatus.SUCCESS:
        data: Dict[str, Any] = {
            "status": "success",
            "run_type": outcome.run_type,
            "repo": outcome.repo_name,
            "shadow": outcome.shadow,
            "correlation_id": outcome.correlation_id,
            "proof": proof_location,
        }
        if ctxpack_digest:
            data["ctxpack_digest"] = ctxpack_digest
        if auto_compiled:
            data["context_auto_compiled"] = True
        if outcome.run_id:
            data["run_id"] = outcome.run_id
        # Include the actual server response payload so callers can read it
        if outcome.response_data:
            data["result"] = outcome.response_data
        next_steps = []
        if outcome.shadow:
            next_steps.append("This was a shadow run — no canonical consequences.")
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Run completed: {outcome.run_type}",
            data=data,
            next_steps=next_steps,
        )

    if outcome.status == OutcomeStatus.ACCEPTED:
        data = {
            "status": "accepted",
            "run_type": outcome.run_type,
            "repo": outcome.repo_name,
            "shadow": outcome.shadow,
            "correlation_id": outcome.correlation_id,
            "proof": proof_location,
        }
        if ctxpack_digest:
            data["ctxpack_digest"] = ctxpack_digest
        if auto_compiled:
            data["context_auto_compiled"] = True
        if outcome.run_id:
            data["run_id"] = outcome.run_id
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Run accepted (async): {outcome.run_type}",
            data=data,
            next_steps=[
                "The run is in progress. Final result is not yet available.",
                f"Check status: keyhole runs status {outcome.run_id or outcome.correlation_id}",
                f"Wait for result: keyhole runs wait {outcome.run_id or outcome.correlation_id}",
                f"Follow: keyhole runs tail {outcome.run_id or outcome.correlation_id}",
            ],
        )

    if outcome.status == OutcomeStatus.DEFERRED:
        data = {
            "status": "deferred",
            "run_type": outcome.run_type,
            "repo": outcome.repo_name,
            "shadow": outcome.shadow,
            "correlation_id": outcome.correlation_id,
            "proof": proof_location,
        }
        if ctxpack_digest:
            data["ctxpack_digest"] = ctxpack_digest
        if auto_compiled:
            data["context_auto_compiled"] = True
        if outcome.run_id:
            data["run_id"] = outcome.run_id
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Run deferred: {outcome.run_type}",
            data=data,
            next_steps=[
                "The run has been deferred by the boundary.",
                "This is not a rejection — it may be processed later.",
                f"Check status: keyhole runs status {outcome.run_id or outcome.correlation_id}",
                f"Wait for result: keyhole runs wait {outcome.run_id or outcome.correlation_id}",
            ],
        )

    # Failure outcomes
    data = {
        "status": outcome.status.value,
        "run_type": outcome.run_type,
        "repo": outcome.repo_name,
        "shadow": outcome.shadow,
        "correlation_id": outcome.correlation_id,
        "error_class": outcome.error_class,
        "reason": outcome.reason,
        "proof": proof_location,
        "retry_safe": outcome.status == OutcomeStatus.TRANSPORT_ERROR,
    }
    if outcome.run_id:
        data["run_id"] = outcome.run_id

    exit_code = (
        EXIT_RUNTIME_UNAVAILABLE
        if outcome.status == OutcomeStatus.TRANSPORT_ERROR
        else EXIT_FAILURE
    )

    return CommandResult(
        command=command_label,
        success=False,
        exit_code=exit_code,
        summary=f"Run failed: {outcome.reason[:120]}" if outcome.reason else "Run failed.",
        data=data,
        next_steps=outcome.repair_guidance or map_repair_guidance(outcome.error_class),
    )
