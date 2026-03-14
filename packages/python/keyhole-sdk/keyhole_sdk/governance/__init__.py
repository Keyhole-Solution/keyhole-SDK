"""Governance proof protocol — RG-01 cross-boundary validation.

CE-V5 — Recursive Governance Proof Test.

Provides the participant-side orchestration for the cross-boundary
governance proof protocol that validates whether an external SDK
repository can participate in governed evolution:

    - Phase 1: Contract registration (SCAFFOLDED)
    - Phase 2: Context inheritance (SUPPORTED)
    - Phase 3: External implementation (SUPPORTED)
    - Phase 4: Local verification (SUPPORTED)
    - Phase 5: Proof submission (SCAFFOLDED)
    - Phase 6: Governance evaluation (SCAFFOLDED)
    - Phase 7: Promotion (SCAFFOLDED)

**Overall support status: SCAFFOLDED** — supported phases work locally,
scaffolded phases await platform-side surface stabilization.
"""

from keyhole_sdk.governance.models import (
    EXPECTED_EVENTS,
    GovernanceEvent,
    GovernancePhase,
    GovernancePhaseResult,
    GovernanceProofResult,
)
from keyhole_sdk.governance.runner import (
    GovernanceProofRunner,
)
from keyhole_sdk.governance.trace import (
    GovernanceTraceBuilder,
)

__all__ = [
    "EXPECTED_EVENTS",
    "GovernanceEvent",
    "GovernancePhase",
    "GovernancePhaseResult",
    "GovernanceProofResult",
    "GovernanceProofRunner",
    "GovernanceTraceBuilder",
]
