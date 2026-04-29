"""Runtime contract repair guidance — SDK-CLIENT-24 §12.5.

Maps client-side and server-classified runtime contract failure modes
into human-readable repair guidance. Server-provided guidance is
preserved as-is when present; this module supplies fallbacks for
common reasons when the server does not echo a repair list.
"""

from __future__ import annotations

from typing import Dict, List

from keyhole_sdk.runtime_contract.models import RuntimeRepairGuidance


_DEFAULT_REPAIRS: Dict[str, List[str]] = {
    "runtime_profiles_missing": [
        "Confirm the MCP server includes SDK-SERVER-24.",
        "Run: keyhole surfaces",
        "Re-run: keyhole runtime profiles",
    ],
    "runtime_surface_unavailable": [
        "Confirm sdk.runtime.surface.get.v1 is exposed by the boundary.",
        "Run: keyhole surfaces",
        "Open a support bundle: keyhole support-bundle <request-id>",
    ],
    "missing_container_digest": [
        "Re-run through the Keyhole container adapter.",
        "Run: keyhole doctor --runtime container",
        "Then retry: keyhole runtime check --mode container --image-digest <digest>",
    ],
    "nonportable_runtime_coupling": [
        "Remove the shared .venv symlink.",
        "Use keyhole.sdk.container.v1 for canonical local execution.",
        "Or submit external.runtime.v1 with portable runtime claims.",
    ],
    "compatibility_check_failed": [
        "Re-run keyhole runtime profiles to confirm boundary posture.",
        "Run: keyhole doctor",
    ],
    "auth_required": [
        "Run: keyhole login",
        "Re-run the runtime command after authentication.",
    ],
}


def map_runtime_repair(reason: str) -> List[str]:
    """Return fallback repair steps for a known reason code."""
    if not reason:
        return []
    return list(_DEFAULT_REPAIRS.get(reason, []))


def fill_repair_defaults(guidance: RuntimeRepairGuidance) -> RuntimeRepairGuidance:
    """Fill in fallback repair steps when the server returned none.

    Server-provided repair always wins. This helper only fills empty lists.
    """
    if guidance.repair:
        return guidance
    fallback = map_runtime_repair(guidance.reason)
    if not fallback:
        return guidance
    return RuntimeRepairGuidance(
        reason=guidance.reason,
        message=guidance.message,
        affected_field=guidance.affected_field,
        repair=fallback,
        next_command=guidance.next_command,
    )
