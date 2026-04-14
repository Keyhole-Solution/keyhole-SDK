"""Budget/limit deterministic renderer — SDK-CLIENT-19 §10.

Produces human-readable output for every outcome family.

Rules:
- Rendering is deterministic: same input always produces same output.
- Never collapse overload into generic failure (§8.1).
- Never tell the builder a request "succeeded" when it was
  deferred or terminated by budget law (§15 prohibitions).
- Match exact taxonomy from §10 (budget_exhausted, deferred, etc.).
"""

from __future__ import annotations

from keyhole_sdk.budget.models import LimitOutcomeClass, LimitResult


def render_budget_summary(result: LimitResult) -> str:
    """Produce a deterministic human-readable summary for a LimitResult.

    The output is concise: a one-paragraph summary with the most important
    fields. The CLI layer adds full detail from result.to_proof_dict().
    """
    label_map = {
        LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY: "SUCCESS (with budget posture)",
        LimitOutcomeClass.BUDGET_EXHAUSTED: "BUDGET EXHAUSTED",
        LimitOutcomeClass.DEFERRED: "DEFERRED (governed pressure handling)",
        LimitOutcomeClass.RATE_LIMITED: "RATE LIMITED",
        LimitOutcomeClass.CONCURRENCY_LIMITED: "CONCURRENCY LIMITED",
        LimitOutcomeClass.UNKNOWN_PRESSURE: "LIMIT / PRESSURE (unrecognized class)",
        LimitOutcomeClass.NO_PRESSURE_DATA: "No budget or pressure data available",
    }
    label = label_map.get(result.outcome_class, str(result.outcome_class.value).upper())

    lines = [f"Limit outcome: {label}"]

    if result.run_id:
        lines.append(f"  run_id: {result.run_id}")
    if result.request_id:
        lines.append(f"  request_id: {result.request_id}")
    if result.limit_class:
        lines.append(f"  limit_class: {result.limit_class}")
    if result.status:
        lines.append(f"  status: {result.status}")

    if result.partial_execution:
        lines.append("  partial_execution: true — run started but did not complete")

    # Budget snapshots (§9)
    for snap in result.budget_snapshots:
        parts = []
        if snap.budget_class:
            parts.append(f"class={snap.budget_class}")
        if snap.budget_used is not None:
            parts.append(f"used={snap.budget_used}")
        if snap.budget_remaining is not None:
            parts.append(f"remaining={snap.budget_remaining}")
        if snap.budget_unit:
            parts.append(f"unit={snap.budget_unit}")
        if snap.near_limit:
            parts.append("NEAR LIMIT")
        if parts:
            lines.append(f"  budget: {', '.join(parts)}")

    if result.retry_after is not None:
        lines.append(f"  retry_after: {result.retry_after}s")

    if result.outcome_class == LimitOutcomeClass.BUDGET_EXHAUSTED:
        lines.append("  → Retrying unchanged is unlikely to succeed.")
    elif result.is_retryable():
        lines.append("  → Retry after guided interval.")

    if result.repair_guidance:
        lines.append("  next:")
        for step in result.repair_guidance[:3]:
            lines.append(f"    - {step}")

    return "\n".join(lines)
