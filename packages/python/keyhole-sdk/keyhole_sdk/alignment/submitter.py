"""Alignment guidance MCP submitter — SDK-CLIENT-11 §5, §6, §13.

Submits an alignment guidance request through the GovernedTransport
layer and classifies the outcome (terminal, accepted, or deferred).

Inherits SDK-CLIENT-15 transport discipline.
Alignment guidance is READ_ONLY (advisory analysis — no repo mutation).
"""

from __future__ import annotations

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
from keyhole_sdk.transport.client import GovernedTransport, TransportResult


def submit_alignment(
    *,
    transport: GovernedTransport,
    request: AlignmentGuidanceRequest,
) -> AlignmentGuidanceResult:
    """Submit an alignment guidance request to the MCP boundary.

    Uses GovernedTransport (X-Request-Id, retry, proof metadata).
    Returns an honest AlignmentGuidanceResult — accepted/deferred
    behavior is preserved, never faked as terminal.

    §13: If the analysis is accepted/deferred, result reflects that
    honestly and preserves follow-up identity.
    """
    from keyhole_sdk.alignment.repair import map_alignment_repair

    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/alignment/guidance",
            operation_name="alignment.guidance",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_transport_exception(exc, request)

    return _classify_outcome(result, request)


def _classify_outcome(
    result: TransportResult,
    request: AlignmentGuidanceRequest,
) -> AlignmentGuidanceResult:
    """Classify the boundary response into an honest guidance result."""
    from keyhole_sdk.alignment.repair import map_alignment_repair

    data = result.data
    status_code = result.status_code
    server_status = data.get("status", "").lower()

    # ── Accepted / Deferred (§13) ─────────────────────────────────────────
    if status_code == 202 or server_status in ("accepted", "pending", "deferred"):
        run_id = data.get("run_id") or data.get("analysis_id")
        # Preserve honest analysis_mode — deferred is not the same as accepted
        honest_mode = "deferred" if server_status == "deferred" else "accepted"
        return AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            items=[],
            next_best_action=(
                f"Analysis {honest_mode} (run_id={run_id}). "
                "Use keyhole runs status to check completion."
            ),
            no_mutation_applied=True,
            correlation_id=request.correlation_id,
            run_id=run_id,
            analysis_mode=honest_mode,
        )

    # ── Server-side error ─────────────────────────────────────────────────
    if status_code >= 400:
        error_class = data.get("error_class", "ServerRejection")
        reason = data.get("reason") or data.get("detail") or f"HTTP {status_code}"
        return AlignmentGuidanceResult(
            success=False,
            readiness=AlignmentReadiness.FOREIGN,
            items=[],
            no_mutation_applied=True,
            correlation_id=request.correlation_id,
            error_class=error_class,
            reason=reason,
            repair_guidance=map_alignment_repair(error_class),
            analysis_mode="terminal",
        )

    # ── Terminal success ──────────────────────────────────────────────────
    raw_items_data: List[Dict[str, Any]] = data.get("guidance_items") or data.get("items") or []
    items = [_parse_item(d) for d in raw_items_data if isinstance(d, dict)]

    # Derive readiness
    readiness_str = data.get("readiness") or data.get("alignment_posture") or ""
    try:
        readiness = AlignmentReadiness(readiness_str)
    except ValueError:
        from keyhole_sdk.alignment.ranker import _derive_readiness
        readiness = _derive_readiness(items)

    next_action = data.get("next_best_action") or _pick_next_action(items)

    verified = [i for i in items if i.state == GuidanceState.VERIFIED]
    inferred = [i for i in items if i.state == GuidanceState.INFERRED]
    gaps = [i for i in items if i.guidance_class == GuidanceClass.GAP]
    warnings = [i for i in items if i.guidance_class == GuidanceClass.WARNING]
    suggestions = [i for i in items if i.guidance_class == GuidanceClass.SUGGESTION]

    return AlignmentGuidanceResult(
        success=True,
        readiness=readiness,
        items=items,
        next_best_action=next_action,
        verified_count=len(verified),
        inferred_count=len(inferred),
        gap_count=len(gaps),
        warning_count=len(warnings),
        suggestion_count=len(suggestions),
        no_mutation_applied=True,
        correlation_id=request.correlation_id,
        run_id=data.get("run_id") or data.get("analysis_id"),
        analysis_mode="terminal",
    )


def _parse_item(d: Dict[str, Any]) -> GuidanceItem:
    """Parse a raw dict into a GuidanceItem, defaulting unknown values."""
    try:
        return GuidanceItem.model_validate(d)
    except Exception:
        # Graceful fallback for malformed items
        return GuidanceItem(
            id=d.get("id", "unknown"),
            **{"class": GuidanceClass.WARNING},
            severity=GuidanceSeverity.LOW,
            confidence=0.5,
            state=GuidanceState.INFERRED,
            title=d.get("title", "Unknown guidance item"),
            detail=d.get("detail", ""),
            repair=d.get("repair", []),
            source=d.get("source", "server"),
        )


def _pick_next_action(items: List[GuidanceItem]) -> Optional[str]:
    """Pick the first repair step from the highest-priority item."""
    for item in sorted(items, key=lambda x: x.sort_key()):
        if item.repair:
            return item.repair[0]
    return None


def _handle_transport_exception(
    exc: Exception,
    request: AlignmentGuidanceRequest,
) -> AlignmentGuidanceResult:
    """Classify transport-level exceptions into honest result."""
    from keyhole_sdk.alignment.repair import map_alignment_repair

    error_class = type(exc).__name__
    return AlignmentGuidanceResult(
        success=False,
        readiness=AlignmentReadiness.FOREIGN,
        items=[],
        no_mutation_applied=True,
        correlation_id=request.correlation_id,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=map_alignment_repair(error_class),
        analysis_mode="terminal",
    )
