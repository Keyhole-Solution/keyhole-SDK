"""Explainability repair guidance — SDK-CLIENT-20 §15.

Maps error classes to deterministic repair steps.

§15: The client must distinguish at least:
  15.1 not_found
  15.2 incomplete_lineage
  15.3 unauthorized
  15.4 server_contract_issue
  15.5 generic guidance for each outcome class
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR: Dict[str, List[str]] = {
    # §15.1 — targeting failure
    "not_found": [
        "Verify the run_id or request_id is correct.",
        "Check that you are using the correct profile (keyhole whoami).",
        "The target may have expired or be outside your tenant scope.",
        "Try: keyhole runs status <run-id> to check reachability.",
    ],
    "run_not_found": [
        "The run ID does not exist or is not visible in this scope.",
        "Verify the run_id with: keyhole runs list",
        "Ensure you are authenticated in the correct profile (keyhole whoami).",
    ],
    "request_not_found": [
        "The request ID does not exist or has no linked run.",
        "Verify the request_id from transport proof or X-Request-Id headers.",
        "Check run records: keyhole runs list",
    ],

    # §15.2 — incomplete lineage
    "incomplete_lineage": [
        "Lineage is still materializing — wait and retry in a few moments.",
        "Try: keyhole explain run <run-id> again after a brief delay.",
        "If lineage remains incomplete, generate a support bundle: keyhole support-bundle <run-id>",
    ],
    "partial_lineage": [
        "Partial lineage was returned — some platform evidence references are not yet available.",
        "Retry: keyhole explain run <run-id> after a short delay.",
        "Generate a support bundle to preserve available truth: keyhole support-bundle <run-id>",
        "If the issue persists, contact support with the bundle.",
    ],

    # §15.3 — authorization
    "unauthorized": [
        "You are not authorized to inspect this run or request.",
        "Check your identity: keyhole whoami",
        "Ensure you are in the correct tenant/org scope.",
        "If this run belongs to a different profile, switch profiles and retry.",
    ],
    "scope_mismatch": [
        "The target is not visible in your current scope.",
        "Check: keyhole whoami and verify tenant/org context.",
        "Switch profiles if needed and retry.",
    ],

    # §15.4 — server contract issues
    "server_contract_issue": [
        "The platform returned an unexpected explainability response.",
        "Preserve available diagnostic artifacts.",
        "Generate a support bundle: keyhole support-bundle <run-id>",
        "Contact support if the issue persists.",
    ],
    "malformed_response": [
        "The server response was malformed or incomplete.",
        "Try again — transient issues may resolve spontaneously.",
        "Generate a support bundle to preserve the diagnostic context.",
    ],

    # §9.1 — accepted
    "accepted": [
        "The run was accepted and is being processed.",
        "Check status: keyhole runs status <run-id>",
        "Wait for terminal state: keyhole runs wait <run-id>",
    ],

    # §9.2 — rejected
    "rejected": [
        "Inspect the rejection reason above for the specific rule that failed.",
        "Review your request structure and context binding.",
        "Check context alignment: keyhole context inspect",
        "If unexpected, generate a support bundle: keyhole support-bundle <run-id>",
    ],

    # §9.3 — replayed
    "replayed": [
        "This request was replayed — the platform reused a prior result.",
        "Inspect the original run: keyhole explain run <replayed-run-id>",
        "If a fresh execution is needed, use a new idempotency key.",
    ],

    # §9.4 — deferred
    "deferred": [
        "The platform deferred this action — it is not rejected.",
        "Resume tracking: keyhole runs resume <run-id>",
        "Wait for terminal state: keyhole runs wait <run-id>",
        "Check budget and pressure posture: keyhole runs budget <run-id>",
    ],

    # §9.5 — budget / rate
    "rate_limited": [
        "Wait before retrying — the platform is enforcing rate policy.",
        "Preserve the same request identity (idempotency key) on retry.",
        "Check budget posture: keyhole runs budget <run-id>",
    ],
    "budget_exhausted": [
        "The run hit a runtime budget ceiling — the execution stopped.",
        "Review budget posture: keyhole runs budget <run-id>",
        "Consider splitting the operation or adjusting workload parameters.",
        "Contact support if this is unexpected: keyhole support-bundle <run-id>",
    ],

    # §9.6 — failed
    "failed": [
        "The run encountered a terminal failure.",
        "Review the failure reason above for the proximate cause.",
        "Check any available proof artifacts.",
        "Generate a support bundle for forensic review: keyhole support-bundle <run-id>",
    ],

    # Generic
    "unknown": [
        "The outcome could not be classified deterministically.",
        "Check run status: keyhole runs status <run-id>",
        "Generate a support bundle: keyhole support-bundle <run-id>",
    ],
    "missing_run_id": [
        "Provide a run ID. Try: keyhole runs list",
    ],
    "missing_request_id": [
        "Provide a request ID from the transcript proof or X-Request-Id header.",
    ],
    "observation_failed": [
        "The platform did not return status for this run.",
        "Check: keyhole runs status <run-id>",
        "Verify connectivity and auth: keyhole whoami",
    ],
}

_DEFAULT_REPAIR = [
    "Check: keyhole runs status <run-id>",
    "Verify identity: keyhole whoami",
    "Generate a support bundle: keyhole support-bundle <run-id>",
]


def map_explain_repair(error_class: str) -> List[str]:
    """Return deterministic repair guidance for the given error class.

    Returns a non-empty list in all cases. Falls back to _DEFAULT_REPAIR
    for unrecognized classes (§20.19 forward-compatibility).
    """
    return list(_REPAIR.get(str(error_class).lower(), _DEFAULT_REPAIR))
