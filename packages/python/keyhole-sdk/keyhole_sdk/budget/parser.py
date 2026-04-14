"""Budget/limit outcome parser — SDK-CLIENT-19 §7, §8, §9.

Maps raw server response dicts into classified LimitResult objects.

Rules:
- Never invent budget classes or values the server did not provide (§15).
- Preserve raw_data in every result for proof.
- Gracefully handle missing/malformed optional fields (§17.4).
- Correctly distinguish transport failures from budget decisions (§8.2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.budget.models import (
    BudgetSnapshot,
    LimitOutcomeClass,
    LimitResult,
)
from keyhole_sdk.budget.repair import map_budget_repair


# ─────────────────────────────────────────────────────────────
# Known overload field names from server contracts
# ─────────────────────────────────────────────────────────────

# Top-level status strings that indicate rate limiting
_RATE_LIMIT_STATUSES = frozenset({
    "rate_limited", "ratelimited", "throttled", "too_many_requests",
})

# Top-level status strings that indicate concurrency limiting
_CONCURRENCY_LIMIT_STATUSES = frozenset({
    "concurrency_limited", "concurrency_exceeded", "slot_unavailable",
    "capacity_exceeded",
})

# Top-level status strings that indicate budget exhaustion
_BUDGET_EXHAUSTED_STATUSES = frozenset({
    "budget_exhausted", "budget_exceeded", "limit_exceeded",
    "resource_exhausted", "quota_exceeded",
})

# Top-level status strings that indicate deferral due to pressure
_DEFERRED_STATUSES = frozenset({
    "deferred", "deferred_pressure", "held", "admission_held",
    "queue_full",
})

# HTTP status codes indicating rate limiting
_RATE_LIMIT_HTTP_CODES = frozenset({429})

# HTTP codes indicating service overload
_OVERLOAD_HTTP_CODES = frozenset({503, 529})


def parse_limit_outcome(
    response_data: Dict[str, Any],
    *,
    http_status_code: Optional[int] = None,
    run_id: str = "",
    request_id: str = "",
    correlation_id: str = "",
) -> LimitResult:
    """Map a server response dict to a classified LimitResult.

    §8.2: Never misclassify transport failure as a budget decision,
    or vice versa. The caller must not pass network exceptions here —
    those are transport errors, not limit outcomes.

    §7.5 forward-compatibility: unknown limit class → UNKNOWN_PRESSURE
    with graceful fallback rendering.

    Args:
        response_data: Parsed JSON dict from the server response.
        http_status_code: HTTP status code (optional) to supplement classification.
        run_id: Run ID from the request or response.
        request_id: X-Request-Id header value.
        correlation_id: Correlation chain ID.

    Returns:
        A LimitResult with outcome class and all available metadata.
    """
    if not response_data:
        # HTTP status codes are authoritative even when the body is empty
        if http_status_code is not None:
            if http_status_code in _RATE_LIMIT_HTTP_CODES:
                return LimitResult(
                    outcome_class=LimitOutcomeClass.RATE_LIMITED,
                    run_id=run_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    retry_safe=True,
                    repair_guidance=map_budget_repair(LimitOutcomeClass.RATE_LIMITED.value),
                    raw_data={},
                )
            if http_status_code in _OVERLOAD_HTTP_CODES:
                return LimitResult(
                    outcome_class=LimitOutcomeClass.DEFERRED,
                    run_id=run_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    is_terminal=False,
                    retry_safe=True,
                    repair_guidance=map_budget_repair(LimitOutcomeClass.DEFERRED.value),
                    raw_data={},
                )
        return LimitResult(
            outcome_class=LimitOutcomeClass.NO_PRESSURE_DATA,
            run_id=run_id,
            request_id=request_id,
            correlation_id=correlation_id,
            raw_data={},
        )

    # Resolve run_id from response if not supplied
    resolved_run_id = run_id or response_data.get("run_id", "")
    resolved_corr = correlation_id or response_data.get("correlation_id", "")

    # ── Step 1: Extract basic status string ──────────────────────────────
    raw_status = str(response_data.get("status", "")).lower().strip()
    limit_outcome_field = str(response_data.get("limit_outcome", "")).lower().strip()
    limit_class_field = str(response_data.get("limit_class", "")).lower().strip()

    # ── Step 2: Classification (§7 families) ─────────────────────────────
    outcome_class = _classify_outcome(
        raw_status=raw_status,
        limit_outcome_field=limit_outcome_field,
        http_status_code=http_status_code,
        response_data=response_data,
    )

    # ── Step 3: Extract budget snapshots (§9) ────────────────────────────
    budget_snapshots = _extract_budget_snapshots(response_data)

    # ── Step 4: Retry guidance ───────────────────────────────────────────
    retry_after = _extract_retry_after(response_data, http_status_code)
    retry_safe = outcome_class in (
        LimitOutcomeClass.RATE_LIMITED,
        LimitOutcomeClass.CONCURRENCY_LIMITED,
        LimitOutcomeClass.DEFERRED,
    )

    # ── Step 5: Partial execution flag ───────────────────────────────────
    partial_execution = bool(
        response_data.get("partial_execution")
        or response_data.get("partially_executed")
        or response_data.get("execution_started")
        or (outcome_class == LimitOutcomeClass.BUDGET_EXHAUSTED)
    )
    if outcome_class == LimitOutcomeClass.BUDGET_EXHAUSTED:
        partial_execution = bool(
            response_data.get("partial_execution", True)
        )

    # ── Step 6: Terminal posture ──────────────────────────────────────────
    is_terminal = outcome_class not in (
        LimitOutcomeClass.DEFERRED,
    )

    # ── Step 7: Repair guidance ──────────────────────────────────────────
    server_repair = response_data.get("repair_guidance") or response_data.get("suggested_actions") or []
    if isinstance(server_repair, list):
        repair_guidance = [str(r) for r in server_repair if r]
    else:
        repair_guidance = []
    if not repair_guidance:
        repair_guidance = map_budget_repair(outcome_class.value)

    # ── Step 8: Effective limit class string ─────────────────────────────
    effective_limit_class = (
        limit_class_field
        or limit_outcome_field
        or _infer_limit_class(budget_snapshots, outcome_class)
    )

    return LimitResult(
        outcome_class=outcome_class,
        run_id=resolved_run_id,
        request_id=request_id,
        status=raw_status or response_data.get("status", ""),
        limit_class=effective_limit_class,
        budget_snapshots=budget_snapshots,
        partial_execution=partial_execution,
        is_terminal=is_terminal,
        retry_after=retry_after,
        retry_safe=retry_safe,
        repair_guidance=repair_guidance,
        correlation_id=resolved_corr,
        raw_data=response_data,
    )


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _classify_outcome(
    *,
    raw_status: str,
    limit_outcome_field: str,
    http_status_code: Optional[int],
    response_data: Dict[str, Any],
) -> LimitOutcomeClass:
    """Map status signals to a LimitOutcomeClass family."""

    # Explicit limit_outcome field from server wins
    if limit_outcome_field:
        if limit_outcome_field in _BUDGET_EXHAUSTED_STATUSES or "budget_exhaust" in limit_outcome_field:
            return LimitOutcomeClass.BUDGET_EXHAUSTED
        if limit_outcome_field in _RATE_LIMIT_STATUSES or "rate_limit" in limit_outcome_field or "throttl" in limit_outcome_field:
            return LimitOutcomeClass.RATE_LIMITED
        if limit_outcome_field in _CONCURRENCY_LIMIT_STATUSES or "concurrency" in limit_outcome_field:
            return LimitOutcomeClass.CONCURRENCY_LIMITED
        if limit_outcome_field in _DEFERRED_STATUSES or "defer" in limit_outcome_field:
            return LimitOutcomeClass.DEFERRED
        if "success" in limit_outcome_field or "budget_visibility" in limit_outcome_field:
            return LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY
        # Unknown from explicit limit_outcome field
        return LimitOutcomeClass.UNKNOWN_PRESSURE

    # HTTP status code classification
    if http_status_code is not None:
        if http_status_code in _RATE_LIMIT_HTTP_CODES:
            return LimitOutcomeClass.RATE_LIMITED
        if http_status_code in _OVERLOAD_HTTP_CODES:
            return LimitOutcomeClass.UNKNOWN_PRESSURE

    # raw status string classification
    if raw_status in _BUDGET_EXHAUSTED_STATUSES or "budget_exhaust" in raw_status:
        return LimitOutcomeClass.BUDGET_EXHAUSTED
    if raw_status in _RATE_LIMIT_STATUSES or "rate_limit" in raw_status or "throttl" in raw_status:
        return LimitOutcomeClass.RATE_LIMITED
    if raw_status in _CONCURRENCY_LIMIT_STATUSES or "concurrency" in raw_status:
        return LimitOutcomeClass.CONCURRENCY_LIMITED
    if raw_status in _DEFERRED_STATUSES or "defer" in raw_status:
        return LimitOutcomeClass.DEFERRED

    # Near-limit warnings on a success outcome
    budget_data = response_data.get("budget") or response_data.get("budget_posture") or {}
    if isinstance(budget_data, dict) and budget_data:
        near = budget_data.get("near_limit") or budget_data.get("warning")
        if near or raw_status in ("success", "completed", "ok"):
            return LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY

    # Budget snapshots present on a success = budget visibility
    snapshots_raw = _get_snapshots_raw(response_data)
    if snapshots_raw and raw_status in ("success", "completed", "ok", ""):
        return LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY

    return LimitOutcomeClass.NO_PRESSURE_DATA


def _get_snapshots_raw(response_data: Dict[str, Any]) -> list:
    """Extract raw budget snapshot(s) from various server field shapes."""
    # Explicit list field
    for key in ("budget_snapshots", "budgets", "budget_dimensions"):
        val = response_data.get(key)
        if isinstance(val, list) and val:
            return val

    # Singular budget object
    for key in ("budget", "budget_posture", "budget_snapshot"):
        val = response_data.get(key)
        if isinstance(val, dict) and val:
            return [val]

    return []


def _extract_budget_snapshots(response_data: Dict[str, Any]) -> List[BudgetSnapshot]:
    """Parse budget snapshot(s) from server response."""
    raw_list = _get_snapshots_raw(response_data)
    snapshots: List[BudgetSnapshot] = []

    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        try:
            snap = BudgetSnapshot(
                budget_class=str(raw.get("budget_class") or raw.get("class") or raw.get("type") or ""),
                budget_used=_safe_float(raw.get("budget_used") or raw.get("used")),
                budget_remaining=_safe_float(raw.get("budget_remaining") or raw.get("remaining")),
                budget_unit=str(raw.get("budget_unit") or raw.get("unit") or ""),
                near_limit=bool(raw.get("near_limit") or raw.get("warning") or False),
                retry_after=_safe_int(raw.get("retry_after")),
            )
            snapshots.append(snap)
        except Exception:
            # Malformed budget snapshot — degrade gracefully (§17.4)
            continue

    return snapshots


def _extract_retry_after(
    response_data: Dict[str, Any],
    http_status_code: Optional[int],
) -> Optional[int]:
    """Extract retry-after guidance in seconds."""
    # Direct top-level field
    val = response_data.get("retry_after") or response_data.get("retry_after_seconds")
    if val is not None:
        return _safe_int(val)

    # From budget object
    budget = response_data.get("budget") or response_data.get("budget_posture") or {}
    if isinstance(budget, dict):
        val = budget.get("retry_after")
        if val is not None:
            return _safe_int(val)

    return None


def _infer_limit_class(
    snapshots: List[BudgetSnapshot],
    outcome_class: LimitOutcomeClass,
) -> str:
    """Infer a limit class string for display when not explicitly supplied."""
    if snapshots:
        classes = [s.budget_class for s in snapshots if s.budget_class]
        if classes:
            return ", ".join(classes)
    if outcome_class == LimitOutcomeClass.BUDGET_EXHAUSTED:
        return "budget"
    if outcome_class == LimitOutcomeClass.RATE_LIMITED:
        return "rate"
    if outcome_class == LimitOutcomeClass.CONCURRENCY_LIMITED:
        return "concurrency_slot"
    return ""


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
