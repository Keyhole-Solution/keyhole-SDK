"""Command-level compatibility evaluation — SDK-CLIENT-21 §16.

Maps CLI commands to their required and optional surface dependencies,
then evaluates each command against the negotiated feature set.

§16 Recommended evaluation flow:
  1. Determine the command's required surfaces.
  2. Compare against negotiated posture.
  3. If any required surface is missing → block.
  4. If only optional surfaces are missing → degrade.
  5. Otherwise → allow.

§14: Block with repair guidance explaining what is missing and why.
§15: Degrade explicitly — bounded, not random.
"""

from __future__ import annotations

from typing import Dict, List

from keyhole_sdk.negotiation.models import (
    CommandCompatibilityResult,
    CommandStatus,
    NegotiatedFeatures,
)
from keyhole_sdk.negotiation.repair import map_negotiation_repair


# ──────────────────────────────────────────────────────────────
# §16 — Command requirements registry
# ──────────────────────────────────────────────────────────────

# Maps command name → required surface names.
# Surface names must match NegotiatedFeatures field names.
COMMAND_REQUIREMENTS: Dict[str, List[str]] = {
    # Identity
    "keyhole whoami": ["authenticated_identity"],
    "keyhole login": [],
    # Run dispatch
    "keyhole run": ["authenticated_identity", "run_dispatch"],
    "keyhole repo register": ["authenticated_identity", "run_dispatch"],
    # Context
    "keyhole context compile": ["authenticated_identity", "context_compile"],
    "keyhole context inspect": ["authenticated_identity", "context_compile"],
    # Explainability
    "keyhole explain run": ["authenticated_identity", "explainability"],
    "keyhole inspect": ["authenticated_identity", "explainability"],
    "keyhole support-bundle": ["authenticated_identity", "support_bundle"],
    # Run observation
    "keyhole runs status": ["authenticated_identity"],
    "keyhole runs wait": ["authenticated_identity"],
    "keyhole runs tail": ["authenticated_identity", "run_tail"],
    "keyhole runs list": ["authenticated_identity"],
    "keyhole runs resume": ["authenticated_identity"],
    "keyhole runs budget": ["authenticated_identity", "budget_visibility"],
    # Account Deregistration (SDK-CLIENT-22)
    "keyhole deregister": ["authenticated_identity", "run_dispatch"],
    # Surfaces inspection (no auth required — reads through public capabilities)
    "keyhole surfaces": [],
    # Doctor — local-only
    "keyhole doctor": [],
    "keyhole validate": [],
}

# Maps command name → optional surface names.
COMMAND_OPTIONAL_SURFACES: Dict[str, List[str]] = {
    "keyhole run": ["run_async_accept"],
    "keyhole runs wait": ["run_async_accept"],
    "keyhole runs resume": ["run_async_accept"],
    "keyhole explain run": ["support_bundle"],
    "keyhole inspect": ["support_bundle"],
    "keyhole deregister": ["explainability", "support_bundle"],
}


def evaluate_command(
    command: str,
    features: NegotiatedFeatures,
) -> CommandCompatibilityResult:
    """§16 — Evaluate a command against the negotiated surface set.

    Returns a :class:`CommandCompatibilityResult` with one of:
      - ALLOWED  — all required and optional surfaces present
      - DEGRADED — all required present; some optional absent
      - BLOCKED  — at least one required surface absent

    Unknown commands (not in registry) are treated as ALLOWED
    with empty surface requirements.
    """
    required = COMMAND_REQUIREMENTS.get(command, [])
    missing_required = [
        s for s in required if not bool(getattr(features, s, False))
    ]

    if missing_required:
        return CommandCompatibilityResult(
            command=command,
            status=CommandStatus.BLOCKED,
            required_missing=missing_required,
            reason=(
                f"Required surface(s) missing for '{command}': "
                + ", ".join(missing_required)
            ),
            repair=_collect_repair(missing_required, command_blocked=True),
        )

    optional = COMMAND_OPTIONAL_SURFACES.get(command, [])
    missing_optional = [
        s for s in optional if not bool(getattr(features, s, False))
    ]

    if missing_optional:
        return CommandCompatibilityResult(
            command=command,
            status=CommandStatus.DEGRADED,
            optional_missing=missing_optional,
            reason=(
                f"Optional surface(s) missing for '{command}': "
                + ", ".join(missing_optional)
                + " — proceeding with reduced capability."
            ),
            repair=_collect_repair(missing_optional, command_blocked=False),
        )

    return CommandCompatibilityResult(
        command=command,
        status=CommandStatus.ALLOWED,
    )


def evaluate_all_commands(
    features: NegotiatedFeatures,
) -> Dict[str, CommandCompatibilityResult]:
    """Evaluate every registered command against the negotiated features.

    Returns a dict of command → CommandCompatibilityResult.
    """
    return {
        cmd: evaluate_command(cmd, features)
        for cmd in COMMAND_REQUIREMENTS
    }


# ── Internal helpers ──────────────────────────────────────────

def _collect_repair(surfaces: List[str], *, command_blocked: bool) -> List[str]:
    """Collect repair steps for absent surfaces."""
    steps: List[str] = []
    for surface in surfaces:
        for step in map_negotiation_repair(surface):
            if step not in steps:
                steps.append(step)
    if command_blocked:
        for step in map_negotiation_repair("command_blocked"):
            if step not in steps:
                steps.append(step)
    else:
        for step in map_negotiation_repair("command_degraded"):
            if step not in steps:
                steps.append(step)
    return steps
