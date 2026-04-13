"""Capability discovery and resolution repair guidance — SDK-CLIENT-08 §18.

Every client-visible failure must include actionable next steps.
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Then retry the search or resolution command.",
    ],
    "NotAuthenticated": [
        "Run: keyhole login",
        "Then retry the search or resolution command.",
    ],
    # Transport failures
    "TransportUnknownError": [
        "Check network connectivity to the MCP boundary.",
        "Retry is safe — the operation may have idempotency protection.",
    ],
    "RetryExhaustedError": [
        "The boundary is unavailable after all retry attempts.",
        "Wait and retry later.",
    ],
    "RuntimeUnavailableError": [
        "The capability registry is temporarily unavailable.",
        "Try again later.",
    ],
    "ConnectionError": [
        "Cannot reach the MCP boundary.",
        "Check network, firewall, and MCP URL configuration.",
        "Retry is safe.",
    ],
    "RateLimitedError": [
        "You are being rate-limited by the boundary.",
        "Wait for the Retry-After period and try again.",
    ],
    "IdempotencyConflictError": [
        "A different payload was sent with the same idempotency key.",
        "If this is a new resolution, use a fresh attempt.",
    ],
    # Resolution-specific
    "AmbiguousResolution": [
        "Multiple providers satisfy the capability — no lawful tie-break exists.",
        "Specify --provider <name> to pin a provider explicitly.",
        "Inspect candidates: keyhole search <capability>",
    ],
    "IncompatibleProviderSet": [
        "Capability exists but no provider satisfies the requested constraints.",
        "Relax version or provider constraints.",
        "Inspect available providers: keyhole search <capability>",
    ],
    "CapabilityNotFound": [
        "The requested capability was not found in the registry.",
        "Check spelling of the capability name.",
        "Try: keyhole search <broader-namespace>",
    ],
    "InvalidLocalDependencyState": [
        "The local repo dependency model is malformed.",
        "Inspect dependencies.yaml for syntax errors.",
        "Run: keyhole validate — to diagnose.",
    ],
    "UnsupportedWriteTarget": [
        "This repo is foreign — in-repo write is not lawful by default.",
        "Use --advisory mode for foreign repos.",
        "Complete alignment before writing dependency state.",
        "Run: keyhole repo register — and alignment steps first.",
    ],
    "ServerRejection": [
        "The boundary rejected the request.",
        "Check the error reason for details.",
        "Inspect ingestion compatibility posture before materializing.",
    ],
    "RegistryUnreachable": [
        "The capability registry is unreachable.",
        "Check network connectivity to the MCP boundary.",
        "Run: keyhole doctor — to diagnose your environment.",
    ],
}


def map_capability_repair(error_class: str) -> List[str]:
    """Map an error class to actionable repair guidance.

    Returns a list of human-readable next steps.
    Unknown error classes get a generic fallback.
    """
    guidance = _REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected error: {error_class}",
        "Try: keyhole search <capability> — to inspect candidates.",
        "Try: keyhole doctor — to diagnose your environment.",
    ]
