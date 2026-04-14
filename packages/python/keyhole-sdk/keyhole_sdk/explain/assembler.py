"""Explainability assembler — SDK-CLIENT-20 §3-§9.

Maps server response dicts into structured explainability models.

§3: Never blur the layers of governed truth (request / run / context /
event+proof / rendered).  Never invent content the server did not return.

§12.3: Fields synthesized client-side from stable server metadata are
flagged with is_reason_inferred=True on RunExplanation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from keyhole_sdk.explain.models import (
    BUNDLE_REQUIRED_SECTIONS,
    ExplainOutcomeClass,
    RequestInspectionResult,
    RunExplanation,
    SupportBundle,
    _NON_TERMINAL_CLASSES,
    _TERMINAL_CLASSES,
)
from keyhole_sdk.explain.repair import map_explain_repair


# ─────────────────────────────────────────────────────────────
# Status-string → ExplainOutcomeClass
# ─────────────────────────────────────────────────────────────

_STATUS_CLASS_MAP: Dict[str, ExplainOutcomeClass] = {
    "success": ExplainOutcomeClass.SUCCEEDED,
    "completed": ExplainOutcomeClass.SUCCEEDED,
    "ok": ExplainOutcomeClass.SUCCEEDED,
    "failed": ExplainOutcomeClass.FAILED,
    "error": ExplainOutcomeClass.FAILED,
    "rejected": ExplainOutcomeClass.REJECTED,
    "denied": ExplainOutcomeClass.REJECTED,
    "cancelled": ExplainOutcomeClass.FAILED,
    "canceled": ExplainOutcomeClass.FAILED,
    "deferred": ExplainOutcomeClass.DEFERRED,
    "accepted": ExplainOutcomeClass.ACCEPTED,
    "pending": ExplainOutcomeClass.ACCEPTED,
    "running": ExplainOutcomeClass.ACCEPTED,
    "in_progress": ExplainOutcomeClass.ACCEPTED,
    "replayed": ExplainOutcomeClass.REPLAYED,
    "rate_limited": ExplainOutcomeClass.RATE_LIMITED,
    "ratelimited": ExplainOutcomeClass.RATE_LIMITED,
    "throttled": ExplainOutcomeClass.RATE_LIMITED,
    "budget_exhausted": ExplainOutcomeClass.BUDGET_EXHAUSTED,
    "budget_exceeded": ExplainOutcomeClass.BUDGET_EXHAUSTED,
    "limit_exceeded": ExplainOutcomeClass.BUDGET_EXHAUSTED,
}


def _classify_from_response(
    response_data: Dict[str, Any],
) -> ExplainOutcomeClass:
    """Derive ExplainOutcomeClass from server response fields.

    Priority:
    1. Explicit outcome_class field
    2. Explicit limit_outcome field
    3. Replay indicators
    4. status / state / run_status string
    5. Partial lineage flag
    6. UNKNOWN fallback
    """
    if not response_data:
        return ExplainOutcomeClass.UNKNOWN

    # 1. Explicit outcome_class
    raw_oc = str(response_data.get("outcome_class", "") or "").lower()
    if raw_oc:
        try:
            return ExplainOutcomeClass(raw_oc)
        except ValueError:
            pass

    # 2. Explicit limit_outcome
    raw_lo = str(response_data.get("limit_outcome", "") or "").lower()
    if raw_lo in ("budget_exhausted", "budget_exceeded", "limit_exceeded"):
        return ExplainOutcomeClass.BUDGET_EXHAUSTED
    if raw_lo in ("rate_limited", "ratelimited", "throttled"):
        return ExplainOutcomeClass.RATE_LIMITED
    if raw_lo in ("deferred", "deferred_pressure"):
        return ExplainOutcomeClass.DEFERRED

    # 3. Replay indicators
    if response_data.get("replayed") or response_data.get("replayed_from"):
        return ExplainOutcomeClass.REPLAYED

    # 4. Status string
    raw_status = str(
        response_data.get("status", "")
        or response_data.get("state", "")
        or response_data.get("run_status", "")
    ).lower()
    if raw_status in _STATUS_CLASS_MAP:
        return _STATUS_CLASS_MAP[raw_status]

    # 5. Partial lineage
    if response_data.get("partial_lineage") or response_data.get("lineage_partial"):
        return ExplainOutcomeClass.PARTIAL_LINEAGE

    return ExplainOutcomeClass.UNKNOWN


def _safe_list(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if isinstance(val, str) and val:
        return [val]
    return []


def _synthesize_reason(
    outcome_class: ExplainOutcomeClass,
    response_data: Dict[str, Any],
) -> tuple[str, bool]:
    """Return (reason_text, is_inferred).

    §12.3: If the server returned an explicit reason, use it verbatim and
    mark is_inferred=False.  If we know the outcome class but no reason was
    returned, synthesize a concise description and mark is_inferred=True.
    """
    # Server-returned reason fields
    for key in ("reason", "message", "explanation", "detail", "rejection_reason"):
        val = response_data.get(key)
        if val and isinstance(val, str):
            return val, False

    # Synthesize from outcome class
    _SYNTHESIZED = {
        ExplainOutcomeClass.ACCEPTED: "Run was accepted by the platform and is being processed.",
        ExplainOutcomeClass.SUCCEEDED: "Run reached a successful terminal state.",
        ExplainOutcomeClass.REJECTED: "Run or request was rejected; see repair guidance.",
        ExplainOutcomeClass.REPLAYED: "Request was replayed from a prior execution — no new action was taken.",
        ExplainOutcomeClass.DEFERRED: "Platform deferred the action; this is a governed pressure response, not a rejection.",
        ExplainOutcomeClass.RATE_LIMITED: "Request was constrained by rate policy.",
        ExplainOutcomeClass.BUDGET_EXHAUSTED: "Run hit a runtime budget ceiling.",
        ExplainOutcomeClass.FAILED: "Run reached a terminal failure state.",
        ExplainOutcomeClass.PARTIAL_LINEAGE: "Lineage is incomplete; some platform references are not yet available.",
        ExplainOutcomeClass.UNKNOWN: "Outcome could not be classified from available server truth.",
    }
    return _SYNTHESIZED.get(outcome_class, "Outcome class not recognized."), True


# ─────────────────────────────────────────────────────────────
# Public assemblers
# ─────────────────────────────────────────────────────────────


def assemble_run_explanation(
    response_data: Optional[Dict[str, Any]],
    *,
    run_id: str = "",
    request_id: str = "",
    correlation_id: str = "",
) -> RunExplanation:
    """Map a server response dict to a classified RunExplanation.

    §3: Does not invent truth the server did not return.
    §12.3: Synthesized fields are flagged is_reason_inferred=True.
    §9.1–9.6: All six canonical outcome classes are handled.

    Args:
        response_data: Parsed JSON dict from the server explainability or
                       status response.  May be None or empty.
        run_id: Run ID from the caller (overrides response if set).
        request_id: Request ID.
        correlation_id: Correlation chain ID.
    """
    data = response_data or {}

    # ── Classification ────────────────────────────────────────
    outcome_class = _classify_from_response(data)

    # ── Identity ──────────────────────────────────────────────
    resolved_run_id = run_id or data.get("run_id", "") or ""
    resolved_req = request_id or data.get("request_id", "") or ""
    resolved_corr = correlation_id or data.get("correlation_id", "") or ""

    # ── Run truth ─────────────────────────────────────────────
    raw_status = (
        data.get("status") or data.get("state") or data.get("run_status") or ""
    )
    run_type = data.get("run_type") or data.get("type") or ""
    is_terminal = outcome_class in _TERMINAL_CLASSES
    shadow = bool(data.get("shadow") or data.get("is_shadow"))
    repo_name = data.get("repo") or data.get("repo_name") or ""

    # ── Context truth ─────────────────────────────────────────
    context_digest = (
        data.get("ctxpack_digest")
        or data.get("context_digest")
        or data.get("context_ref")
        or ""
    )
    context_ref = data.get("context_ref") or data.get("context_label") or context_digest or ""

    # ── Reason ───────────────────────────────────────────────
    reason, is_reason_inferred = _synthesize_reason(outcome_class, data)
    reason_code = data.get("reason_code") or data.get("error_class") or ""

    # ── Evidence ──────────────────────────────────────────────
    event_refs = _safe_list(data.get("event_refs") or data.get("events") or [])
    proof_refs = _safe_list(data.get("proof_refs") or data.get("proof_digests") or [])
    proof_digest = data.get("proof_digest") or data.get("digest") or ""

    # ── Budget surface (inheritance from SDK-CLIENT-19) ───────
    budget_summary = data.get("budget_summary") or ""
    limit_outcome = data.get("limit_outcome") or ""

    # ── Replay ───────────────────────────────────────────────
    replayed_from = data.get("replayed_from") or data.get("prior_run_id") or ""
    idempotency_key = data.get("idempotency_key") or data.get("x_idempotency_key") or ""

    # ── Partial lineage ───────────────────────────────────────
    has_partial = bool(
        data.get("partial_lineage")
        or data.get("lineage_partial")
        or outcome_class == ExplainOutcomeClass.PARTIAL_LINEAGE
    )
    lineage_note = data.get("lineage_note") or (
        "Some platform evidence references are not yet available." if has_partial else ""
    )

    # ── Repair guidance ───────────────────────────────────────
    server_repair = _safe_list(data.get("repair_guidance") or data.get("suggested_actions") or [])
    repair = server_repair or map_explain_repair(outcome_class.value)

    # ── Summary short text (for bundle) ──────────────────────
    summary = (
        data.get("summary")
        or f"Run {resolved_run_id or '<unknown>'}: {outcome_class.value}"
    )

    return RunExplanation(
        run_id=resolved_run_id,
        request_id=resolved_req,
        correlation_id=resolved_corr,
        outcome_class=outcome_class,
        status=str(raw_status),
        run_type=str(run_type),
        is_terminal=is_terminal,
        shadow=shadow,
        repo_name=str(repo_name),
        context_digest=str(context_digest),
        context_ref=str(context_ref),
        reason=reason,
        reason_code=str(reason_code),
        is_reason_inferred=is_reason_inferred,
        event_refs=event_refs,
        proof_refs=proof_refs,
        proof_digest=str(proof_digest),
        budget_summary=str(budget_summary),
        limit_outcome=str(limit_outcome),
        replayed_from=str(replayed_from),
        idempotency_key=str(idempotency_key),
        repair_guidance=repair,
        summary=str(summary),
        has_partial_lineage=has_partial,
        lineage_note=str(lineage_note),
        raw_data=data,
    )


def assemble_request_inspection(
    response_data: Optional[Dict[str, Any]],
    *,
    request_id: str = "",
) -> RequestInspectionResult:
    """Map a server response dict to a RequestInspectionResult.

    §7.2: Must surface disposition flags, run linkage, proof refs.
    """
    data = response_data or {}

    outcome_class = _classify_from_response(data)

    resolved_req = request_id or data.get("request_id", "") or ""
    run_id = data.get("run_id") or ""
    corr = data.get("correlation_id") or ""
    idempotency_key = data.get("idempotency_key") or ""

    raw_status = (
        data.get("status") or data.get("state") or ""
    )
    executed = bool(
        data.get("executed")
        or run_id
        or outcome_class in (
            ExplainOutcomeClass.ACCEPTED,
            ExplainOutcomeClass.SUCCEEDED,
            ExplainOutcomeClass.FAILED,
            ExplainOutcomeClass.BUDGET_EXHAUSTED,
        )
    )
    replayed = bool(
        data.get("replayed")
        or data.get("replayed_from")
        or outcome_class == ExplainOutcomeClass.REPLAYED
    )
    deferred = bool(
        data.get("deferred")
        or outcome_class == ExplainOutcomeClass.DEFERRED
    )

    context_ref = data.get("context_ref") or data.get("ctxpack_digest") or ""
    event_refs = _safe_list(data.get("event_refs") or [])
    proof_refs = _safe_list(data.get("proof_refs") or [])

    reason, _ = _synthesize_reason(outcome_class, data)
    server_repair = _safe_list(data.get("repair_guidance") or [])
    repair = server_repair or map_explain_repair(outcome_class.value)

    return RequestInspectionResult(
        request_id=resolved_req,
        correlation_id=corr,
        idempotency_key=idempotency_key,
        run_id=str(run_id),
        outcome_class=outcome_class,
        status=str(raw_status),
        executed=executed,
        replayed=replayed,
        deferred=deferred,
        context_ref=str(context_ref),
        event_refs=event_refs,
        proof_refs=proof_refs,
        reason=reason,
        repair_guidance=repair,
        raw_data=data,
    )


def assemble_support_bundle(
    *,
    run_id: str = "",
    request_id: str = "",
    explanation: Optional[RunExplanation] = None,
    inspection: Optional[RequestInspectionResult] = None,
    cli_version: str = "0.2.0",
) -> SupportBundle:
    """Assemble a SupportBundle from available explanation data.

    §10: If sections are unavailable, include explicit omission notes
    rather than silently dropping expected content.

    §10 safety: Must not include secrets, tokens, or credential stores.
    """
    resolved_run_id = run_id or (explanation.run_id if explanation else "") or ""
    resolved_req = request_id or (explanation.request_id if explanation else "") or (
        inspection.request_id if inspection else ""
    ) or ""

    summary_md = _build_summary_md(resolved_run_id, resolved_req, explanation, inspection)
    request_section = _build_request_section(resolved_req, explanation, inspection)
    run_section = _build_run_section(resolved_run_id, explanation)
    context_section = _build_context_section(explanation)
    events_section = _build_events_section(explanation, inspection)
    proof_refs_section = _build_proof_refs_section(explanation, inspection)
    outcome_section = _build_outcome_section(resolved_run_id, resolved_req, explanation, inspection)
    repair_section = _build_repair_section(explanation, inspection)
    metadata_section = {
        "cli_version": cli_version,
        "run_id": resolved_run_id,
        "request_id": resolved_req,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "bundle_version": "1.0",
    }

    # Detect missing sections
    missing: list[str] = []
    omission_notes: dict[str, str] = {}

    if not run_section:
        missing.append("run")
        omission_notes["run"] = "No run data available."
    if not context_section:
        missing.append("context")
        omission_notes["context"] = "No context reference available."
    if not events_section.get("refs"):
        missing.append("events")
        omission_notes["events"] = "No event references in available data."
    if not proof_refs_section.get("refs"):
        missing.append("proof_refs")
        omission_notes["proof_refs"] = "No proof references in available data."

    return SupportBundle(
        run_id=resolved_run_id,
        request_id=resolved_req,
        summary_md=summary_md,
        request=request_section,
        run=run_section,
        context=context_section,
        events=events_section,
        proof_refs=proof_refs_section,
        outcome=outcome_section,
        repair=repair_section,
        metadata=metadata_section,
        missing_sections=missing,
        omission_notes=omission_notes,
        cli_version=cli_version,
    )


# ─────────────────────────────────────────────────────────────
# Support bundle section builders
# ─────────────────────────────────────────────────────────────


def _build_summary_md(
    run_id: str,
    request_id: str,
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> str:
    lines = ["# Support Bundle Summary\n"]

    if run_id:
        lines.append(f"**Run ID:** {run_id}")
    if request_id:
        lines.append(f"**Request ID:** {request_id}")

    if explanation:
        lines.append(f"**Outcome:** {explanation.outcome_class.value}")
        lines.append(f"**Status:** {explanation.status or 'unknown'}")
        if explanation.reason:
            lines.append(f"\n**Reason:** {explanation.reason}")
        if explanation.has_partial_lineage:
            lines.append(f"\n**Note:** {explanation.lineage_note or 'Partial lineage.'}")

    lines.append(f"\n---\n*Generated by Keyhole CLI at {datetime.now(timezone.utc).isoformat()}*\n")
    return "\n".join(lines)


def _build_request_section(
    request_id: str,
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> Dict[str, Any]:
    section: Dict[str, Any] = {}
    if request_id:
        section["request_id"] = request_id
    if explanation:
        if explanation.idempotency_key:
            section["idempotency_key"] = explanation.idempotency_key
        if explanation.correlation_id:
            section["correlation_id"] = explanation.correlation_id
    if inspection:
        section["request_id"] = inspection.request_id
        if inspection.idempotency_key:
            section["idempotency_key"] = inspection.idempotency_key
        if inspection.correlation_id:
            section["correlation_id"] = inspection.correlation_id
    return section


def _build_run_section(
    run_id: str,
    explanation: Optional[RunExplanation],
) -> Dict[str, Any]:
    if not explanation and not run_id:
        return {}
    section: Dict[str, Any] = {"run_id": run_id or (explanation.run_id if explanation else "")}
    if explanation:
        section.update({
            "status": explanation.status,
            "run_type": explanation.run_type,
            "is_terminal": explanation.is_terminal,
            "shadow": explanation.shadow,
            "repo_name": explanation.repo_name,
        })
    return section


def _build_context_section(explanation: Optional[RunExplanation]) -> Dict[str, Any]:
    if not explanation:
        return {}
    if not explanation.context_digest and not explanation.context_ref:
        return {}
    return {
        "context_digest": explanation.context_digest,
        "context_ref": explanation.context_ref,
    }


def _build_events_section(
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> Dict[str, Any]:
    refs: List[str] = []
    if explanation:
        refs.extend(explanation.event_refs)
    if inspection:
        refs.extend(inspection.event_refs)
    return {"refs": sorted(set(refs))}


def _build_proof_refs_section(
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> Dict[str, Any]:
    refs: List[str] = []
    if explanation:
        refs.extend(explanation.proof_refs)
        if explanation.proof_digest:
            refs.append(explanation.proof_digest)
    if inspection:
        refs.extend(inspection.proof_refs)
    return {"refs": sorted(set(refs))}


def _build_outcome_section(
    run_id: str,
    request_id: str,
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> Dict[str, Any]:
    section: Dict[str, Any] = {
        "run_id": run_id,
        "request_id": request_id,
    }
    if explanation:
        section["outcome_class"] = explanation.outcome_class.value
        section["status"] = explanation.status
        section["is_terminal"] = explanation.is_terminal
        section["reason"] = explanation.reason
        section["is_reason_inferred"] = explanation.is_reason_inferred
        section["limit_outcome"] = explanation.limit_outcome
        if explanation.has_partial_lineage:
            section["partial_lineage"] = True
            section["lineage_note"] = explanation.lineage_note
    elif inspection:
        section["outcome_class"] = inspection.outcome_class.value
        section["executed"] = inspection.executed
        section["replayed"] = inspection.replayed
        section["deferred"] = inspection.deferred
    else:
        section["outcome_class"] = "unknown"
    return section


def _build_repair_section(
    explanation: Optional[RunExplanation],
    inspection: Optional[RequestInspectionResult],
) -> Dict[str, Any]:
    steps: List[str] = []
    if explanation:
        steps.extend(explanation.repair_guidance)
    elif inspection:
        steps.extend(inspection.repair_guidance)
    return {"steps": steps}
