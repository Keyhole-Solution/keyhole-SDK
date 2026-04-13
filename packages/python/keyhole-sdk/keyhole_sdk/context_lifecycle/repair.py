"""Context repair guidance — SDK-CLIENT-16 §14.

Maps context-related error classes to concrete, actionable repair guidance.
Distinguishes local misuse, missing input, remote rejection, unknown digest,
stale digest, and incompatible context/run combination.
"""

from __future__ import annotations

from typing import Dict, List

_CONTEXT_REPAIR_MAP: Dict[str, List[str]] = {
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Re-authenticate and try again.",
    ],
    # Transport failures
    "TransportUnknownError": [
        "Check network connectivity to the MCP boundary.",
        "Retry is safe for context compile (read-only operation).",
    ],
    "RetryExhaustedError": [
        "The boundary is unavailable after all retry attempts.",
        "Wait and retry later.",
    ],
    "RuntimeUnavailableError": [
        "The runtime returned an error. It may be temporarily unavailable.",
        "Try again later.",
    ],
    # Rate limiting
    "RateLimitedError": [
        "You are being rate-limited by the boundary.",
        "Wait for the Retry-After period and try again.",
    ],
    # Digest errors
    "unknown_digest": [
        "The requested digest is not known to the boundary.",
        "Run: keyhole context compile — to compile a fresh context.",
        "Run: keyhole context inspect --digest <digest> — to verify a known digest.",
    ],
    "stale_digest": [
        "The requested digest is stale or expired.",
        "Run: keyhole context compile — to compile a fresh context.",
    ],
    "malformed_digest": [
        "The digest format is invalid.",
        "Expected a hex string (32–128 chars) or prefixed format (e.g. sha256:<hex>).",
    ],
    # Compile failures
    "compile_rejected": [
        "The boundary rejected the context compile request.",
        "Check that the repo scaffold and declarations are valid.",
        "Run: keyhole init vertical — if the scaffold is missing.",
    ],
    # Context binding failures
    "missing_context": [
        "Governed runs require explicit context binding.",
        "Run: keyhole context compile — to compile context first.",
        "Or use: keyhole run --context auto — to compile and bind automatically.",
    ],
    "incompatible_context": [
        "The context digest is incompatible with the requested run type.",
        "Run: keyhole context compile — to compile a fresh, compatible context.",
    ],
    # Scaffold errors
    "ScaffoldMissing": [
        "Run: keyhole init vertical",
        "Ensure you are in a governed repo directory.",
    ],
    # Preflight errors
    "ContextPreflightFailure": [
        "Preflight checks failed before context operation.",
        "Review the error reason and follow the repair guidance above.",
    ],
    # Inspect errors
    "inspect_failed": [
        "Context inspection failed.",
        "Verify the digest is correct.",
        "Run: keyhole context compile — to get a valid digest.",
    ],
    # Public endpoint errors
    "PublicEndpointError": [
        "The boundary rejected the request.",
        "Check the error detail for the specific reason.",
    ],
    # Idempotency
    "IdempotencyConflictError": [
        "A different payload was sent with the same idempotency key.",
        "Retry the operation — a fresh key will be generated.",
    ],
}


def map_context_repair(error_class: str) -> List[str]:
    """Return repair guidance for a context-related error class.

    Falls back to generic guidance — never a dead end.
    """
    guidance = _CONTEXT_REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected context error: {error_class}",
        "Run: keyhole context compile — to compile context.",
        "Run: keyhole context inspect --digest <digest> — to inspect a known digest.",
    ]
