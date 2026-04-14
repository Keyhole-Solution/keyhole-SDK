"""Budget/limit outcome repair guidance — SDK-CLIENT-19 §11.

Maps outcome classes to concrete next-action repair steps.

§11 contract: Every overload or limit outcome must map to one or
more concrete next actions when the server provides enough information.

The client must never leave the user with only "Request failed."
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # §10.2 budget_exhausted
    "budget_exhausted": [
        "Inspect the exhausted budget class and narrow the run scope.",
        "Reduce output volume or target set before retrying.",
        "Use --shadow for exploratory work to avoid consuming bounded budgets.",
        "Contact your tenant admin if the budget appears misconfigured.",
        "Run: keyhole runs status <run-id> — to retrieve the full terminal state.",
    ],

    # §10.3 deferred
    "deferred": [
        "The request was deferred due to governed pressure handling — not rejected.",
        "The run may still execute when platform pressure reduces.",
        "Run: keyhole runs status <run-id> — to check if the run has started.",
        "Run: keyhole runs wait <run-id> — to await terminal state.",
        "Run: keyhole runs resume <identifier> — to reconnect to a deferred run.",
    ],

    # §10.4 rate_limited
    "rate_limited": [
        "The request was rate limited — this is not a semantic contract failure.",
        "Wait for the indicated retry interval, then retry.",
        "Run: keyhole runs status <run-id> — to check if an earlier run already started.",
        "Reduce submission rate if the rate limit persists.",
        "Check your tenant rate posture if limits seem too low.",
    ],

    # §10.4 concurrency_limited
    "concurrency_limited": [
        "The request was gated by a concurrency slot limit.",
        "Wait for current runs to complete before submitting new work.",
        "Run: keyhole runs list — to see which runs are currently active.",
        "Run: keyhole runs wait <run-id> — for each active run before retrying.",
        "Reduce the number of simultaneous governed runs in your tenant.",
    ],

    # §7.5 unknown_pressure
    "unknown_pressure": [
        "The server returned an unrecognized limit or pressure category.",
        "Run: keyhole runs status <run-id> — to retrieve full run metadata.",
        "Inspect the proof artifact for raw server response details.",
        "Retry after a short delay — this may be a transient platform condition.",
        "If the issue persists, contact support with the run_id and request_id.",
    ],

    # §7.1 success with budget visibility
    "success_with_budget_visibility": [
        "The run completed successfully.",
        "Review the budget posture summary for any near-limit warnings.",
        "Consider reducing run scope if any budgets are near exhaustion.",
    ],

    # No pressure data
    "no_pressure_data": [
        "No budget or limit information was returned by the server.",
        "Run: keyhole runs status <run-id> — to request fresh status.",
    ],

    # Transport or client errors that surface here
    "TransportUnknownError": [
        "A transport-level error occurred when fetching budget posture.",
        "Check network connectivity and retry.",
        "Verify the MCP boundary is reachable: keyhole doctor",
    ],
    "AuthenticationError": [
        "Not authenticated. Run: keyhole login",
        "Then retry: keyhole runs budget <run-id>",
    ],
    "NotAuthenticated": [
        "Not authenticated. Run: keyhole login",
        "Then retry: keyhole runs budget <run-id>",
    ],
    "MissingRunId": [
        "A run ID is required. Use: keyhole runs budget <run-id>",
        "Run: keyhole runs list — to find recent run IDs.",
    ],
}

_DEFAULT_REPAIR = [
    "Inspect the proof artifact for raw server details.",
    "Run: keyhole runs status <run-id> — for current run state.",
    "Retry after a short delay if this is a transient condition.",
]


def map_budget_repair(outcome_class: str) -> List[str]:
    """Map a limit outcome class string to concrete repair guidance.

    Returns non-empty list for any input (§11 guarantee).
    """
    return list(_REPAIR_MAP.get(outcome_class, _DEFAULT_REPAIR))
