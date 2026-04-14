"""Alignment guidance repair guidance — SDK-CLIENT-11 §16.

Maps error classes to concrete, actionable repair steps.
Guidance must never be a dead end (§8.3 message quality rule).
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Re-authenticate and try again.",
    ],
    "NotAuthenticated": [
        "Run: keyhole login to authenticate.",
        "Ensure your session has not expired.",
    ],
    # Transport failures
    "TransportUnknownError": [
        "Check network connectivity to the MCP boundary.",
        "Retry is safe — alignment guidance is read-only.",
    ],
    "RetryExhaustedError": [
        "The boundary is unavailable after all retry attempts.",
        "Wait and retry later.",
    ],
    "RuntimeUnavailableError": [
        "The alignment guidance service is temporarily unavailable.",
        "Try again later.",
    ],
    "ConnectionError": [
        "Cannot reach the MCP boundary.",
        "Check your MCP URL and network connection.",
    ],
    # Rate limiting
    "RateLimitedError": [
        "You are being rate-limited. Wait for the Retry-After period.",
        "Reduce request frequency.",
    ],
    # Alignment-specific failures
    "NoAnalysisArtifact": [
        "No prior analysis artifact found for this repo.",
        "Run keyhole ingest . to generate an analysis first.",
        "Or provide an explicit --analysis-id.",
    ],
    "MalformedServerResponse": [
        "The server returned an unexpected response shape.",
        "Update keyhole CLI to ensure contract compatibility.",
        "File an issue if the problem persists.",
    ],
    "CorruptedSavedArtifact": [
        "A saved guidance artifact appears corrupt or incomplete.",
        "Rerun: keyhole ingest . to regenerate analysis.",
    ],
    "UnsupportedSchemaVersion": [
        "The server returned an unsupported guidance schema version.",
        "Update keyhole CLI: pip install --upgrade keyhole-cli",
    ],
    "MissingRepoContext": [
        "Repo context is required but was not found.",
        "Run: keyhole ingest . to establish context first.",
    ],
    "RenderFailure": [
        "Guidance rendering encountered an error.",
        "Check that your guidance artifact is not empty.",
        "Rerun with --shadow for a fresh advisory pass.",
    ],
    "AcceptedDeferredNotReady": [
        "Guidance analysis was accepted but is not yet complete.",
        "Use: keyhole runs status <run-id> to check progress.",
    ],
    "ServerRejection": [
        "The alignment boundary rejected the request.",
        "Check the error reason for details.",
        "Try: keyhole ingest --shadow . for a low-risk exploratory pass.",
    ],
    # Generic fallback
    "_default": [
        "Rerun: keyhole ingest . to regenerate analysis.",
        "Check your credentials: keyhole login",
        "Use --shadow mode for a safe advisory pass.",
    ],
}


def map_alignment_repair(error_class: str) -> List[str]:
    """Return repair guidance for a given alignment error class.

    Always returns at least one concrete action — never a dead end.
    """
    return list(_REPAIR_MAP.get(error_class, _REPAIR_MAP["_default"]))
