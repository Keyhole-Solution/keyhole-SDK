"""`keyhole align` — alignment guidance command.

SDK-CLIENT-11: Alignment Guidance.

Turns repo analysis results into actionable, deterministic builder guidance.

Supports:
  keyhole align .
  keyhole align . --analysis-id <id>
  keyhole align --from-ingestion <correlation-id>
  keyhole align . --shadow
  keyhole align . --json

Never mutates the target repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from keyhole_sdk.alignment.models import (
    AlignmentGuidanceRequest,
    AlignmentGuidanceResult,
    AlignmentReadiness,
    GuidanceClass,
    GuidanceItem,
    GuidanceSeverity,
    GuidanceState,
)
from keyhole_sdk.alignment.ranker import render_guidance
from keyhole_sdk.alignment.proof import emit_alignment_proof
from keyhole_sdk.alignment.repair import map_alignment_repair
from keyhole_sdk.alignment.submitter import submit_alignment
from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    CommandResult,
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
)
from keyhole_sdk.config import DEFAULT_BASE_URL

_DEFAULT_STATE_SUBDIR = "state"


def run_align(
    *,
    repo_path: str = ".",
    analysis_id: str = "",
    from_ingestion: str = "",
    shadow: bool = False,
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
    local_only: bool = False,
) -> CommandResult:
    """Execute ``keyhole align``.

    Renders deterministic alignment guidance for the given repo.
    Never mutates the target repo (§14 no-silent-mutation rule).

    When no MCP connection is configured (local_only=True), renders
    guidance from locally available artifacts only.
    """
    command_label = "keyhole align"

    # ── Validate repo path ────────────────────────────────────────────────
    target = Path(repo_path).resolve()
    if not target.exists():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Repo path does not exist: {target}",
            data={"error_class": "MissingRepoContext", "is_local": True},
            next_steps=map_alignment_repair("MissingRepoContext"),
        )

    # ── Build correlation ID ──────────────────────────────────────────────
    correlation_id = from_ingestion or generate_request_id()

    # ── Resolve keyhole home / state dir ─────────────────────────────────
    kh_home = Path(keyhole_home) if keyhole_home else None
    state_dir = (kh_home or (Path.home() / ".keyhole")) / _DEFAULT_STATE_SUBDIR

    # ── Load saved ingestion outcome artifact if available ────────────────
    ingestion_outcome = _load_ingestion_outcome(state_dir, from_ingestion or analysis_id)

    # ── Build request ─────────────────────────────────────────────────────
    request = AlignmentGuidanceRequest(
        repo_identity=target.name,
        repo_path=str(target),
        analysis_id=analysis_id or from_ingestion,
        ingestion_outcome=ingestion_outcome,
        shadow=shadow,
        correlation_id=correlation_id,
    )

    # ── Local-only fast path ──────────────────────────────────────────────
    # If we have local items from a saved ingestion, render without MCP.
    if local_only or not _has_token(keyhole_home):
        guidance_items = _extract_items_from_ingestion(ingestion_outcome)
        result = render_guidance(request, raw_items=guidance_items)
        result.correlation_id = correlation_id

        # Emit proof
        try:
            proof_dir = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id=correlation_id,
                request_dict=request.to_proof_dict(),
                result=result,
            )
            proof_path = str(proof_dir)
        except Exception:
            proof_path = ""

        return _build_command_result(
            result=result,
            command_label=command_label,
            proof_path=proof_path,
            mode="local-only",
        )

    # ── Governed path: submit to MCP boundary ────────────────────────────
    try:
        store = CredentialStore(store_dir=kh_home)
        session = store.load()
        if not session or not session.access_token:
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_FAILURE,
                summary="Not authenticated. Run: keyhole login",
                data={"error_class": "NotAuthenticated", "is_local": True},
                next_steps=["Run: keyhole login", "Then retry: keyhole align ."],
            )

        token = session.access_token
        auth = BearerTokenProvider(token=token)
        transport = GovernedTransport(base_url=mcp_url, auth_provider=auth)

        result = submit_alignment(transport=transport, request=request)

    except Exception as exc:
        error_class = type(exc).__name__
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Alignment guidance failed: {exc}",
            data={"error_class": error_class, "is_local": True},
            next_steps=map_alignment_repair(error_class),
        )

    # ── Emit proof ────────────────────────────────────────────────────────
    try:
        proof_dir = emit_alignment_proof(
            state_dir=state_dir,
            correlation_id=correlation_id,
            request_dict=request.to_proof_dict(),
            result=result,
        )
        proof_path = str(proof_dir)
    except Exception:
        proof_path = ""

    return _build_command_result(
        result=result,
        command_label=command_label,
        proof_path=proof_path,
        mode="governed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _build_command_result(
    *,
    result: AlignmentGuidanceResult,
    command_label: str,
    proof_path: str,
    mode: str,
) -> CommandResult:
    """Build a CommandResult from an AlignmentGuidanceResult."""
    if not result.success:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=result.reason or "Alignment guidance failed.",
            data={
                "error_class": result.error_class,
                "readiness": result.readiness.value,
                "mode": mode,
            },
            next_steps=result.repair_guidance or map_alignment_repair(result.error_class),
        )

    if result.is_accepted_or_deferred():
        run_ref = result.run_id or result.correlation_id
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=(
                f"Analysis accepted (run_id={run_ref}). "
                "Use keyhole runs status to check completion."
            ),
            data={
                "readiness": result.readiness.value,
                "analysis_mode": result.analysis_mode,
                "run_id": result.run_id,
                "correlation_id": result.correlation_id,
                "mode": mode,
            },
            next_steps=[
                f"keyhole runs status {run_ref}",
                "Retry: keyhole align . — once analysis is complete.",
            ],
        )

    # Build human-friendly guidance summary data
    data: Dict[str, Any] = {
        "readiness": result.readiness.value,
        "verified_count": result.verified_count,
        "inferred_count": result.inferred_count,
        "gap_count": result.gap_count,
        "warning_count": result.warning_count,
        "suggestion_count": result.suggestion_count,
        "no_mutation_applied": result.no_mutation_applied,
        "mode": mode,
    }
    if result.run_id:
        data["run_id"] = result.run_id
    if proof_path:
        data["proof_path"] = proof_path

    next_steps: List[str] = []
    if result.next_best_action:
        next_steps.append(result.next_best_action)
    next_steps.append("No changes were applied. Review guidance before taking action.")

    # Build item summary for data
    if result.items:
        data["items"] = [i.to_dict() for i in result.items]

    summary = (
        f"Alignment posture: {result.readiness.value} — "
        f"{result.verified_count} verified, {result.inferred_count} inferred, "
        f"{result.gap_count} gaps."
    )

    return CommandResult(
        command=command_label,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=summary,
        data=data,
        next_steps=next_steps,
    )


def _load_ingestion_outcome(
    state_dir: Path,
    correlation_id: str,
) -> Optional[Dict[str, Any]]:
    """Try to load a saved ingestion outcome artifact for local rendering."""
    if not correlation_id:
        return None
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in correlation_id)
    candidate = state_dir / "ingest" / safe[:64] / "response.json"
    if candidate.exists():
        import json
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _extract_items_from_ingestion(
    ingestion_outcome: Optional[Dict[str, Any]],
) -> List[GuidanceItem]:
    """Convert saved ingestion outcome fields into local GuidanceItems."""
    if not ingestion_outcome:
        return []

    items: List[GuidanceItem] = []

    # Warnings from ingestion → warnings
    for w in ingestion_outcome.get("warnings", []):
        text = w if isinstance(w, str) else str(w)
        items.append(GuidanceItem.model_validate({
            "id": f"warning.ingestion.{len(items)}",
            "class": GuidanceClass.WARNING.value,
            "severity": GuidanceSeverity.MEDIUM.value,
            "confidence": 0.9,
            "state": GuidanceState.VERIFIED.value,
            "title": text[:80],
            "detail": text,
            "repair": ["Review and address before proceeding."],
            "source": "ingestion_outcome",
        }))

    # Suggested actions from ingestion → suggestions
    for s in ingestion_outcome.get("suggested_actions", ingestion_outcome.get("next_steps", [])):
        text = s if isinstance(s, str) else str(s)
        items.append(GuidanceItem.model_validate({
            "id": f"suggestion.ingestion.{len(items)}",
            "class": GuidanceClass.SUGGESTION.value,
            "severity": GuidanceSeverity.LOW.value,
            "confidence": 0.8,
            "state": GuidanceState.INFERRED.value,
            "title": text[:80],
            "detail": text,
            "repair": [text],
            "source": "ingestion_outcome",
        }))

    return items


def _has_token(keyhole_home: str) -> bool:
    """Check whether a valid auth token exists."""
    try:
        store_dir = Path(keyhole_home) if keyhole_home else None
        store = CredentialStore(store_dir=store_dir)
        session = store.load()
        return bool(session and session.access_token)
    except Exception:
        return False
