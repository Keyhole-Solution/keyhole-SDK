"""Alignment guidance ranker and renderer — SDK-CLIENT-11 §9–§12.

Deterministic ranking, grouping, readiness computation, and
next-best-action selection from a list of GuidanceItems.

§9: Deterministic ordering rules
§10: Readiness/compatibility rendering
§11: Next-best action contract
§12: Rendering requirements
§3: Verified vs inferred must never be blurred
§14: No silent repo mutation
"""

from __future__ import annotations

from typing import List, Optional

from keyhole_sdk.alignment.models import (
    AlignmentGuidanceRequest,
    AlignmentGuidanceResult,
    AlignmentReadiness,
    GuidanceClass,
    GuidanceItem,
    GuidanceSeverity,
    GuidanceState,
)


def render_guidance(
    request: AlignmentGuidanceRequest,
    *,
    raw_items: Optional[List[GuidanceItem]] = None,
) -> AlignmentGuidanceResult:
    """Deterministically rank, group, and render alignment guidance.

    §9: Items are sorted by class → state → severity → confidence → id.
    §10: Readiness is derived from the ranked item set.
    §11: Next-best action is selected from the highest-priority item.
    §14: No mutation is applied; no_mutation_applied always True.
    """
    # Prefer explicit raw_items arg; fall back to request-embedded items
    items = list(raw_items) if raw_items is not None else list(request.guidance_items)

    # Sort deterministically per §9
    items.sort(key=lambda x: x.sort_key())

    verified = [i for i in items if i.state == GuidanceState.VERIFIED]
    inferred = [i for i in items if i.state == GuidanceState.INFERRED]
    gaps = [i for i in items if i.guidance_class == GuidanceClass.GAP]
    warnings = [i for i in items if i.guidance_class == GuidanceClass.WARNING]
    suggestions = [i for i in items if i.guidance_class == GuidanceClass.SUGGESTION]

    readiness = _derive_readiness(items)
    next_action = _select_next_best_action(items, readiness)

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
        analysis_mode="terminal",
    )


def _derive_readiness(items: List[GuidanceItem]) -> AlignmentReadiness:
    """§10: Derive alignment posture from the current item set.

    Precedence:
    1. Any HIGH-severity VERIFIED gap → BLOCKED (if reason is blocking)
    2. Verified gaps present → PARTIALLY_ALIGNED (not ready for runs)
    3. Only inferred items → FOREIGN (early stage, observer posture)
    4. Warnings only, no gaps → REGISTRATION_READY
    5. No issues → RUN_READY

    Foreign repos with no items get FOREIGN posture, not success.
    """
    verified_gaps = [
        i for i in items
        if i.state == GuidanceState.VERIFIED and i.guidance_class == GuidanceClass.GAP
    ]
    high_verified_gaps = [g for g in verified_gaps if g.severity == GuidanceSeverity.HIGH]
    verified_items = [i for i in items if i.state == GuidanceState.VERIFIED]

    if high_verified_gaps:
        return AlignmentReadiness.BLOCKED

    if verified_gaps:
        return AlignmentReadiness.PARTIALLY_ALIGNED

    if not verified_items and items:
        # All inferred — early foreign stage
        return AlignmentReadiness.FOREIGN

    if not items:
        # No items at all — assume foreign (not yet analyzed)
        return AlignmentReadiness.FOREIGN

    warnings_only = all(
        i.guidance_class in (GuidanceClass.WARNING, GuidanceClass.SUGGESTION, GuidanceClass.INFERENCE)
        for i in items
    )
    if warnings_only:
        return AlignmentReadiness.REGISTRATION_READY

    return AlignmentReadiness.RUN_READY


def _select_next_best_action(
    items: List[GuidanceItem],
    readiness: AlignmentReadiness,
) -> Optional[str]:
    """§11: Return the single most important next action.

    The first ranked item's first repair step is the next-best action
    when available. Falls back to readiness-derived generic guidance.
    """
    # Use items already in deterministic sort order
    for item in items:
        if item.repair:
            return item.repair[0]

    # Readiness-derived fallback
    _READINESS_ACTIONS = {
        AlignmentReadiness.FOREIGN: (
            "This repo is still foreign. Complete registration readiness before governed run attempts."
        ),
        AlignmentReadiness.PARTIALLY_ALIGNED: (
            "Resolve verified gaps before attempting governed runs."
        ),
        AlignmentReadiness.BLOCKED: (
            "Resolve all HIGH-severity verified gaps before proceeding."
        ),
        AlignmentReadiness.REGISTRATION_READY: (
            "Run keyhole repo register to complete governed registration."
        ),
        AlignmentReadiness.RUN_READY: (
            "Run keyhole run --context auto to begin a governed execution."
        ),
    }
    return _READINESS_ACTIONS.get(readiness)
