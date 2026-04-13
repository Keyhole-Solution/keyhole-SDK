"""Run lifecycle repair guidance — SDK-CLIENT-17 §17.

Maps error classes to concrete, actionable repair steps for
async run observation and resume failures.
"""

from __future__ import annotations

from typing import Dict, List


_REPAIR_MAP: Dict[str, List[str]] = {
    # §17.1: Non-terminal — not failure
    "non_terminal": [
        "The run is accepted but not yet complete.",
        "Check status: keyhole runs status <run-id>",
        "Wait for result: keyhole runs wait <run-id>",
    ],
    # §17.2: Observation failure
    "observation_failed": [
        "Status retrieval failed — this does NOT mean execution failed.",
        "Retry: keyhole runs status <run-id>",
        "Or wait: keyhole runs wait <run-id>",
    ],
    "status_retrieval_failed": [
        "Status retrieval failed.",
        "Check network connectivity to the MCP boundary.",
        "Retry: keyhole runs status <run-id>",
        "Observation failure does not mean execution failed.",
    ],
    # §17.3: Terminal failure
    "terminal_failure": [
        "The run completed with a failure or denial.",
        "Inspect local proof: proof_bundle/core/runs/<run-id>/",
        "Use richer explain/support surfaces when available.",
    ],
    # §17.4: Resume ambiguity
    "resume_ambiguous": [
        "Cannot determine which run to reconnect to confidently.",
        "Provide the exact run-id or request-id.",
        "List recent runs: keyhole runs list (when available)",
        "Check local proof: .keyhole/state/runs/",
    ],
    "missing_identifier": [
        "No run ID or request ID provided.",
        "Provide: keyhole runs resume <run-id>",
    ],
    # §17.5: Protocol failure
    "protocol_error": [
        "The boundary returned an invalid accepted/deferred envelope.",
        "Missing run_id in accepted response.",
        "Retry the run or contact support.",
    ],
    "missing_run_id": [
        "The boundary accepted the run but did not return a run_id.",
        "This is a protocol-level issue.",
        "Check local proof for the correlation_id.",
    ],
    # Wait failures
    "wait_timeout": [
        "The run did not reach terminal state within the poll limit.",
        "Try again: keyhole runs wait <run-id>",
        "Or check: keyhole runs status <run-id>",
        "The run may still be in progress.",
    ],
    "wait_interrupted": [
        "Wait was interrupted before terminal state.",
        "Resume: keyhole runs wait <run-id>",
        "Or check: keyhole runs status <run-id>",
    ],
    # Auth failures
    "AuthenticationError": [
        "Run: keyhole login",
        "Re-authenticate and try again.",
    ],
    # Transport failures
    "TransportUnknownError": [
        "Check network connectivity to the MCP boundary.",
        "Retry is safe for observation commands.",
    ],
    "RetryExhaustedError": [
        "The boundary is unavailable after all retry attempts.",
        "Wait and retry later.",
    ],
    "RuntimeUnavailableError": [
        "The runtime returned an error. It may be temporarily unavailable.",
        "Try again later.",
    ],
    # Malformed ID
    "malformed_run_id": [
        "The run ID format is invalid.",
        "Check the run ID and try again.",
        "Run IDs are typically alphanumeric with dashes or underscores.",
    ],
}


def map_run_lifecycle_repair(error_class: str) -> List[str]:
    """Return repair guidance for the given error class.

    Falls back to generic guidance if the class is unknown.
    """
    guidance = _REPAIR_MAP.get(error_class)
    if guidance:
        return list(guidance)
    return [
        f"Unexpected error: {error_class}",
        "Check: keyhole runs status <run-id>",
        "Observation failure does not mean execution failed.",
    ]
