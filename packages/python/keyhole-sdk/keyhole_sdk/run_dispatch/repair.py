"""Repair guidance mapping — SDK-CLIENT-09 §15.

Maps error classes to concrete, actionable repair guidance.
Guidance must never be a dead end (§12, §15).
"""

from __future__ import annotations

from typing import Dict, List

# §15: Known error class → repair guidance mapping
_REPAIR_MAP: Dict[str, List[str]] = {
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Re-authenticate and try again.",
    ],
    # Transport failures
    "TransportUnknownError": [
        "Check network connectivity to the MCP boundary.",
        "Retry is safe — the operation has idempotency protection.",
    ],
    "RetryExhaustedError": [
        "The boundary is unavailable after all retry attempts.",
        "Wait and retry later. The operation preserved its idempotency key.",
    ],
    "RuntimeUnavailableError": [
        "The runtime returned an error. It may be temporarily unavailable.",
        "Try again later.",
    ],
    # Idempotency
    "IdempotencyConflictError": [
        "A different payload was sent with the same idempotency key.",
        "If this is a new operation, use a fresh idempotency key.",
    ],
    "MissingIdempotencyKeyError": [
        "This is an SDK-internal error. The write operation requires an idempotency key.",
        "Update the SDK to the latest version.",
    ],
    "RateLimitedError": [
        "You are being rate-limited by the boundary.",
        "Wait for the Retry-After period and try again.",
    ],
    # Request errors
    "PublicEndpointError": [
        "The boundary rejected the request.",
        "Check the error detail for the specific reason.",
        "Run: keyhole validate — to check local declaration files.",
    ],
    # Scaffold errors
    "ScaffoldMissing": [
        "Run: keyhole init vertical",
        "Ensure you are in a governed repo directory.",
    ],
    # Run-type errors
    "InvalidRunType": [
        "Choose a valid run-type from capabilities.",
        "Run: keyhole run --run-type <valid-type>",
        "Do not guess run-type names.",
    ],
    # Preflight errors
    "PreflightFailure": [
        "Preflight checks failed before dispatch.",
        "Review the error reason and follow the repair guidance above.",
    ],
}


def map_repair_guidance(error_class: str) -> List[str]:
    """Return repair guidance for the given error class.

    Falls back to generic guidance if the class is unknown.
    """
    guidance = _REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected error: {error_class}",
        "Try: keyhole run --shadow — for a low-risk first pass.",
        "Try: keyhole validate — to check local declaration files.",
    ]
