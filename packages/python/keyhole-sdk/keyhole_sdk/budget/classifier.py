"""Budget/limit outcome classifier helpers — SDK-CLIENT-19.

§15: Platform truthfulness under pressure.
  - is_pressure_outcome(): tests if an outcome represents runtime pressure
  - classify_retry_posture(): maps outcome to 'retry_later', 'retry_safe',
                              'do_not_retry', 'unknown' without guessing
    platform internals
"""

from __future__ import annotations

from keyhole_sdk.budget.models import (
    LimitOutcomeClass,
    LimitResult,
    _HARD_TERMINAL_OUTCOMES,
    _TEMPORARY_OUTCOMES,
)


def is_pressure_outcome(outcome_class: LimitOutcomeClass) -> bool:
    """Return True if *outcome_class* represents runtime pressure.

    SUCCESS_WITH_BUDGET_VISIBILITY and NO_PRESSURE_DATA are not pressure
    conditions — they are informational or no-data states.
    """
    return outcome_class not in (
        LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY,
        LimitOutcomeClass.NO_PRESSURE_DATA,
    )


def classify_retry_posture(result: LimitResult) -> str:
    """Map *result* to a retry posture string.

    Returns one of:
      'retry_later'   — transient pressure; safe to retry after back-off
      'retry_safe'    — server explicitly declares retry safe
      'do_not_retry'  — hard terminal pressure; retrying will not help
      'unknown'       — posture cannot be determined

    §15.3: Do not collapse overload into generic failure — classify it.
    """
    if result.outcome_class in _TEMPORARY_OUTCOMES:
        return "retry_later"
    if result.outcome_class in _HARD_TERMINAL_OUTCOMES:
        if result.retry_safe:
            # Server said retry_safe despite hard outcome — trust server
            return "retry_safe"
        return "do_not_retry"
    if result.retry_safe:
        return "retry_safe"
    if result.outcome_class == LimitOutcomeClass.UNKNOWN_PRESSURE:
        return "unknown"
    # SUCCESS or NO_PRESSURE_DATA — no retry posture needed
    return "unknown"
