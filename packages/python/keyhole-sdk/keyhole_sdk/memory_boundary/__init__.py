"""Memory Boundary Enforcement — SDK-CLIENT-18.

Enforces the memory containment doctrine at the public client boundary.

The public SDK must not expose direct canonical memory access.
All memory-relevant behavior must be reached through:
  - governed context  (context compile / inspect)
  - governed runs     (run --context <digest>)
  - proof / explain   (read-only governed artifacts)

This module provides:
  - reject_direct_memory_access()     — raises DirectMemoryAccessNotAllowed
  - get_memory_boundary_repair()      — returns lawful alternative guidance
  - emit_memory_boundary_proof()      — writes enforcement proof bundle
  - MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES — canonical alternatives list
  - MEMORY_BOUNDARY_REJECTION_MESSAGE   — canonical rejection string
"""

from keyhole_sdk.memory_boundary.enforcer import (
    MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES,
    MEMORY_BOUNDARY_REJECTION_MESSAGE,
    get_memory_boundary_repair,
    reject_direct_memory_access,
)
from keyhole_sdk.memory_boundary.proof import emit_memory_boundary_proof

__all__ = [
    "MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES",
    "MEMORY_BOUNDARY_REJECTION_MESSAGE",
    "emit_memory_boundary_proof",
    "get_memory_boundary_repair",
    "reject_direct_memory_access",
]
