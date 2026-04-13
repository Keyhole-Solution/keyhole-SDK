"""Registration repair guidance — SDK-CLIENT-07 §14.

Maps error classes to concrete, actionable repair guidance.
Guidance must never be a dead end.
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Then re-run: keyhole repo register",
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
        "The registration service is temporarily unavailable.",
        "Try again later.",
    ],
    # Idempotency
    "IdempotencyConflictError": [
        "A different payload was sent with the same idempotency key.",
        "If this is a new registration, use a fresh attempt.",
    ],
    "RateLimitedError": [
        "You are being rate-limited by the boundary.",
        "Wait for the Retry-After period and try again.",
    ],
    # Registration-specific errors — §14
    "MissingNativeArtifacts": [
        "This repo is not ready for native registration.",
        "Run: keyhole ingest .",
        "Review compatibility posture and alignment guidance.",
        "Then re-run: keyhole repo register --from-ingest <ingest-id>",
    ],
    "MissingIngestionReference": [
        "Ingestion-backed registration requires a prior ingestion reference.",
        "Run: keyhole ingest .",
        "Then: keyhole repo register --from-ingest <ingest-id>",
    ],
    "WeakIngestionPosture": [
        "This repo is not yet registration-ready.",
        "Review inferred structure and compatibility posture.",
        "Address the suggested alignment steps.",
        "Then retry registration.",
    ],
    "MissingCapabilityPassport": [
        "Generate or repair the capability passport, then re-run registration.",
        "Run: keyhole repo register — once the passport is in place.",
    ],
    "InvalidRepoPath": [
        "The specified repository path does not exist or is not a directory.",
        "Check the path and try again: keyhole repo register --path <valid-path>",
    ],
    "ServerRejection": [
        "The registration boundary rejected the request.",
        "Check the error reason for details.",
        "Try: keyhole repo register --shadow — for an observational pass.",
    ],
    "NotAuthenticated": [
        "Run: keyhole login",
        "Then re-run: keyhole repo register",
    ],
    # Request shape
    "PublicEndpointError": [
        "The boundary rejected the request payload.",
        "Check error details for the specific reason.",
    ],
}


def map_registration_repair(error_class: str) -> List[str]:
    """Return repair guidance for the given error class.

    Falls back to generic guidance if the class is unknown.
    """
    guidance = _REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected error: {error_class}",
        "Try: keyhole repo register --shadow — for an observational pass.",
        "Try: keyhole doctor — to diagnose your environment.",
    ]
