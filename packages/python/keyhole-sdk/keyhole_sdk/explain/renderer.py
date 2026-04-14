"""Explainability renderer — SDK-CLIENT-20 §8, §12.

Deterministic human-readable rendering for run explanations,
request inspections, and support bundle summaries.

§12.1: Readability first — concise but complete.
§12.2: Stable section ordering for the same outcome class.
§12.3: Distinguish known (server-returned) from inferred.
§12.4: Repair guidance mandatory on non-success.
§12.5: Non-terminal runs must not be rendered as completed.
"""

from __future__ import annotations

from keyhole_sdk.explain.models import (
    ExplainOutcomeClass,
    RequestInspectionResult,
    RunExplanation,
)


# §12.2 — stable output labels per outcome class
_OUTCOME_LABELS: dict[ExplainOutcomeClass, str] = {
    ExplainOutcomeClass.ACCEPTED: "Accepted — in progress",
    ExplainOutcomeClass.SUCCEEDED: "Succeeded",
    ExplainOutcomeClass.REJECTED: "Rejected",
    ExplainOutcomeClass.REPLAYED: "Replayed (prior result reused)",
    ExplainOutcomeClass.DEFERRED: "Deferred — governed pressure response",
    ExplainOutcomeClass.RATE_LIMITED: "Rate-limited",
    ExplainOutcomeClass.BUDGET_EXHAUSTED: "Budget exhausted",
    ExplainOutcomeClass.FAILED: "Failed",
    ExplainOutcomeClass.PARTIAL_LINEAGE: "Partial lineage",
    ExplainOutcomeClass.UNKNOWN: "Outcome unknown",
}

_INSPECT_LABELS: dict[ExplainOutcomeClass, str] = {
    ExplainOutcomeClass.ACCEPTED: "Request accepted — run in flight",
    ExplainOutcomeClass.SUCCEEDED: "Request succeeded",
    ExplainOutcomeClass.REJECTED: "Request rejected",
    ExplainOutcomeClass.REPLAYED: "Request replayed",
    ExplainOutcomeClass.DEFERRED: "Request deferred",
    ExplainOutcomeClass.RATE_LIMITED: "Request rate-limited",
    ExplainOutcomeClass.BUDGET_EXHAUSTED: "Request hit budget ceiling",
    ExplainOutcomeClass.FAILED: "Request failed",
    ExplainOutcomeClass.PARTIAL_LINEAGE: "Request — partial lineage",
    ExplainOutcomeClass.UNKNOWN: "Request outcome unknown",
}


def render_explanation(explanation: RunExplanation) -> str:
    """Render a RunExplanation as a deterministic human-readable string.

    §8: Sections in canonical order (Summary → Identity → Request/Run →
        Context → Evidence → Outcome → Reason → Repair → Proof refs).
    §12.5: Never says "completed" or "succeeded" for non-terminal classes.
    §12.4: Always ends with repair guidance on non-success.
    """
    label = _OUTCOME_LABELS.get(explanation.outcome_class, explanation.outcome_class.value)
    lines: list[str] = []

    # ── §8.1 Summary ─────────────────────────────────────────
    lines.append(f"[EXPLAIN] {label}")
    lines.append("")

    # ── §8.2 Identity / Scope ─────────────────────────────────
    if explanation.run_id:
        lines.append(f"Run ID:       {explanation.run_id}")
    if explanation.request_id:
        lines.append(f"Request ID:   {explanation.request_id}")
    if explanation.run_type:
        lines.append(f"Run Type:     {explanation.run_type}")
    if explanation.repo_name:
        lines.append(f"Repo:         {explanation.repo_name}")
    if explanation.shadow:
        lines.append("Mode:         shadow (observational)")

    # ── §8.3 Run Mapping ───────────────────────────────────────
    if explanation.status:
        lines.append(f"Status:       {explanation.status}")
    terminal_txt = "yes" if explanation.is_terminal else "no"
    lines.append(f"Terminal:     {terminal_txt}")
    if explanation.idempotency_key:
        lines.append(f"Idempotency:  {explanation.idempotency_key}")
    if explanation.replayed_from:
        lines.append(f"Replayed from: {explanation.replayed_from}")

    # ── §8.4 Context Used ─────────────────────────────────────
    if explanation.context_digest or explanation.context_ref:
        lines.append("")
        lines.append("Context:")
        ref = explanation.context_ref or explanation.context_digest
        lines.append(f"  Digest/Ref: {ref}")

    # ── §8.5 Key Evidence ─────────────────────────────────────
    if explanation.event_refs or explanation.proof_refs or explanation.proof_digest:
        lines.append("")
        lines.append("Evidence:")
        for ref in explanation.event_refs:
            lines.append(f"  event: {ref}")
        for ref in explanation.proof_refs:
            lines.append(f"  proof: {ref}")
        if explanation.proof_digest:
            lines.append(f"  digest: {explanation.proof_digest}")

    # ── §8.5 Budget surface (inheritance from SDK-CLIENT-19) ──
    if explanation.limit_outcome or explanation.budget_summary:
        lines.append("")
        lines.append("Budget / Limit:")
        if explanation.limit_outcome:
            lines.append(f"  Limit outcome: {explanation.limit_outcome}")
        if explanation.budget_summary:
            lines.append(f"  {explanation.budget_summary}")

    # ── §8.6 Outcome ──────────────────────────────────────────
    lines.append("")
    lines.append(f"Outcome: {label}")

    # ── §8.7 Reason and Repair ────────────────────────────────
    if explanation.reason:
        lines.append("")
        inferred_note = " (inferred)" if explanation.is_reason_inferred else ""
        lines.append(f"Reason{inferred_note}: {explanation.reason}")

    if explanation.has_partial_lineage and explanation.lineage_note:
        lines.append("")
        lines.append(f"Lineage note: {explanation.lineage_note}")

    # §12.4 — repair guidance mandatory on non-success
    if explanation.repair_guidance:
        lines.append("")
        lines.append("Next steps:")
        for step in explanation.repair_guidance[:5]:
            lines.append(f"  - {step}")

    # ── §8.8 Proof / Support References ──────────────────────
    if explanation.run_id:
        lines.append("")
        lines.append("Support:")
        lines.append(f"  keyhole support-bundle {explanation.run_id}")

    return "\n".join(lines)


def render_inspection(result: RequestInspectionResult) -> str:
    """Render a RequestInspectionResult as human-readable text.

    §12.2: Stable section ordering per outcome class.
    §12.4: Repair guidance mandatory on non-success.
    """
    label = _INSPECT_LABELS.get(result.outcome_class, result.outcome_class.value)
    lines: list[str] = []

    # Summary
    lines.append(f"[INSPECT] {label}")
    lines.append("")

    # Identity
    if result.request_id:
        lines.append(f"Request ID:   {result.request_id}")
    if result.run_id:
        lines.append(f"Run ID:       {result.run_id}")
    if result.idempotency_key:
        lines.append(f"Idempotency:  {result.idempotency_key}")

    # Disposition flags
    lines.append("")
    lines.append(f"Executed:     {'yes' if result.executed else 'no'}")
    lines.append(f"Replayed:     {'yes' if result.replayed else 'no'}")
    lines.append(f"Deferred:     {'yes' if result.deferred else 'no'}")

    if result.status:
        lines.append(f"Status:       {result.status}")

    # Context
    if result.context_ref:
        lines.append("")
        lines.append(f"Context ref:  {result.context_ref}")

    # Evidence
    if result.event_refs or result.proof_refs:
        lines.append("")
        lines.append("Evidence:")
        for ref in result.event_refs:
            lines.append(f"  event: {ref}")
        for ref in result.proof_refs:
            lines.append(f"  proof: {ref}")

    # Reason
    if result.reason:
        lines.append("")
        lines.append(f"Reason: {result.reason}")

    # §12.4 repair guidance
    if result.repair_guidance:
        lines.append("")
        lines.append("Next steps:")
        for step in result.repair_guidance[:5]:
            lines.append(f"  - {step}")

    return "\n".join(lines)
