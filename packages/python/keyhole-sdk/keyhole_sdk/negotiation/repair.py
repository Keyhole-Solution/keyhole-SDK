"""Repair guidance — SDK-CLIENT-21 §14 §15.

Maps surface absence or compatibility error codes to deterministic
repair steps for builder-facing presentation.

§14 Required UX: fail-closed messaging must explain what is missing,
    why it is required, which command is blocked, how to recover.
§15 Required UX: degraded mode must be explicit and bounded.
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR: Dict[str, List[str]] = {
    # ── §8.1 Required surface absence ────────────────────────
    "authenticated_identity": [
        "The boundary has not declared an identity endpoint.",
        "Verify you are connecting to the correct MCP URL: keyhole doctor",
        "Try: keyhole login to establish an authenticated session.",
        "Check that the MCP server is running and reachable.",
    ],
    "run_dispatch": [
        "The boundary has not declared a run dispatch endpoint.",
        "Verify the MCP URL and contract version: keyhole doctor",
        "This boundary may not support governed run dispatch at this contract version.",
        "Check that the server is provisioned and accessible.",
    ],
    # ── §8.2 Optional surface absence ─────────────────────────
    "run_async_accept": [
        "Accepted/deferred async run semantics are not available on this boundary.",
        "Runs may execute synchronously or return inline results instead.",
        "Check server capabilities: keyhole surfaces",
        "Refer to server upgrade notes if async acceptance is expected.",
    ],
    "context_compile": [
        "Context compile/inspect surfaces are not available on this boundary.",
        "Context-bound commands (keyhole context compile, keyhole context inspect) will not function.",
        "Check surface posture: keyhole surfaces",
        "Contact the boundary operator if context surfaces are expected.",
    ],
    "explainability": [
        "Run explainability surface is not available on this boundary.",
        "keyhole explain run will return a 'surface unavailable' response.",
        "Core run commands may still be available.",
        "Check: keyhole surfaces to inspect current posture.",
    ],
    "support_bundle": [
        "Support bundle retrieval is not available on this boundary.",
        "Local support artifacts can still be generated.",
        "Server-enriched bundle behavior is unavailable.",
        "Check: keyhole surfaces --json for current posture.",
    ],
    "run_tail": [
        "Run tail/follow observation is not available on this boundary.",
        "Use keyhole runs status <run-id> to poll run state instead.",
        "Check: keyhole surfaces for current observation capabilities.",
    ],
    "budget_visibility": [
        "Budget and limit visibility is not available on this boundary.",
        "Run budget inspection (keyhole runs budget) will not return server data.",
        "Check: keyhole surfaces to inspect current posture.",
    ],
    # ── §8.3 Transitional / informational ─────────────────────
    "context_required_for_runs": [
        "The server declares that context binding is required for governed runs.",
        "Ensure context is compiled before dispatching runs: keyhole context compile",
        "Check context state: keyhole context inspect",
    ],
    "idempotency_required": [
        "The server declares that idempotency keys are required for write-bearing commands.",
        "All write-bearing SDK calls automatically include idempotency keys (SDK-CLIENT-15).",
        "Ensure you are using the GovernedTransport for all write operations.",
    ],
    # ── Transport / connectivity failures ─────────────────────
    "transport_failure": [
        "Could not reach the MCP boundary to fetch surface declarations.",
        "Check your network connection and MCP URL configuration.",
        "Try: keyhole doctor to run connectivity diagnostics.",
        "If operating offline, some commands may not be available.",
    ],
    "malformed_capabilities": [
        "The capabilities response from the server could not be parsed.",
        "This may indicate a version mismatch or a misconfigured server.",
        "Try: keyhole doctor",
        "Ensure the server is running a compatible contract version.",
    ],
    # ── Command-level block messages ──────────────────────────
    "command_blocked": [
        "This command requires a surface that the live boundary does not declare.",
        "Run: keyhole surfaces to inspect which surfaces are missing.",
        "Contact the boundary operator if the surface is expected.",
    ],
    "command_degraded": [
        "This command will proceed with reduced capability.",
        "Some optional features will not be available.",
        "Run: keyhole surfaces --json to see the full negotiated posture.",
    ],
}

# Fallback for unknown error codes
_FALLBACK_REPAIR = [
    "Run: keyhole surfaces to inspect current surface negotiation posture.",
    "Run: keyhole doctor to check connectivity and configuration.",
]


def map_negotiation_repair(reason: str) -> List[str]:
    """Return deterministic repair steps for a negotiation reason code.

    Always returns a non-empty list — falls back to surface inspection
    guidance for unknown codes.
    """
    return list(_REPAIR.get(reason, _FALLBACK_REPAIR))
