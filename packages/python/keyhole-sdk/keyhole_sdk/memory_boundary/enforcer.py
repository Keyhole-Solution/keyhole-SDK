"""Memory boundary enforcement logic — SDK-CLIENT-18.

Provides deterministic rejection with repair guidance for any attempt
to reach canonical memory directly through the public SDK surface.
"""

from __future__ import annotations

from typing import Optional

from keyhole_sdk.exceptions import DirectMemoryAccessNotAllowed

# Canonical list of lawful alternatives builders should use instead of
# direct canonical memory access.
MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES: list[str] = [
    "keyhole context compile",
    "keyhole context inspect",
    "keyhole run --context <digest>",
    "keyhole runs status <run-id>",
]

# Canonical rejection message emitted to builders who attempt illegal direct
# memory access through the CLI or SDK.
MEMORY_BOUNDARY_REJECTION_MESSAGE: str = (
    "REJECT — Direct canonical memory access is not exposed by the public SDK.\n"
    "Why: memory is governed through context, run, proof, and explainability surfaces.\n"
    "Try:\n"
    "  keyhole context compile\n"
    "  keyhole context inspect\n"
    "  keyhole run --context <digest>"
)


def get_memory_boundary_repair() -> list[str]:
    """Return the canonical list of lawful alternatives for memory access.

    Used as repair guidance when DirectMemoryAccessNotAllowed is raised or
    when the CLI rejects a direct-memory attempt.
    """
    return list(MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES)


def reject_direct_memory_access(
    attempted_surface: str = "",
    *,
    extra_context: Optional[str] = None,
) -> None:
    """Raise DirectMemoryAccessNotAllowed unconditionally.

    Call this from any internal path that would otherwise provide direct
    canonical memory access, to enforce the memory containment doctrine.

    Parameters
    ----------
    attempted_surface:
        Human-readable description of what the caller tried to access
        (e.g. 'memory.query', 'MemoryQueryClient', 'client.memory.search').
    extra_context:
        Optional additional guidance to include in repair output.
    """
    guidance = get_memory_boundary_repair()
    if extra_context:
        guidance = [extra_context] + guidance
    raise DirectMemoryAccessNotAllowed(
        attempted_surface=attempted_surface,
        repair_guidance=guidance,
    )
