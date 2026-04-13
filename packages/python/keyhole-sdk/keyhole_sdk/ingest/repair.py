"""Ingestion repair guidance — SDK-CLIENT-10 §15.

Maps error classes to concrete, actionable repair guidance.
Guidance must never be a dead end.
"""

from __future__ import annotations

from typing import Dict, List

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
        "The ingestion service is temporarily unavailable.",
        "Try again later.",
    ],
    # Idempotency
    "IdempotencyConflictError": [
        "A different payload was sent with the same idempotency key.",
        "If this is a new ingestion, retry with --shadow for a fresh attempt.",
    ],
    "RateLimitedError": [
        "You are being rate-limited by the boundary.",
        "Wait for the Retry-After period and try again.",
    ],
    # Ingestion-specific errors
    "InvalidRepoPath": [
        "The specified repository path does not exist or is not a directory.",
        "Check the path and try again: keyhole ingest <valid-path>",
    ],
    "EmptyPackage": [
        "No files were included after filtering.",
        "Check your --include and --exclude patterns.",
        "Try: keyhole ingest <path> --include '*.py' — to include specific files.",
    ],
    "PackageTooLarge": [
        "The ingestion package exceeds the size limit.",
        "Use --max-bytes to constrain package size.",
        "Use --exclude to skip large directories.",
    ],
    "ServerRejection": [
        "The ingestion boundary rejected the request.",
        "Check the error reason for details.",
        "Try: keyhole ingest --shadow — for a low-risk exploratory pass.",
    ],
    # Request shape
    "PublicEndpointError": [
        "The boundary rejected the request payload.",
        "Check error details for the specific reason.",
    ],
}


def map_ingestion_repair(error_class: str) -> List[str]:
    """Return repair guidance for the given error class.

    Falls back to generic guidance if the class is unknown.
    """
    guidance = _REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected error: {error_class}",
        "Try: keyhole ingest --shadow — for a low-risk exploratory pass.",
        "Try: keyhole doctor — to diagnose your environment.",
    ]
