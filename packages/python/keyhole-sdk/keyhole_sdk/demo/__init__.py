"""Recursive demo readiness — keyhole_sdk.demo.

CE-V5-S42-09: Recursive Demo Readiness Pack.

Provides :class:`DemoFlowRunner` to compose the full external-side
recursive governance demo into a scriptable, deterministic flow.

The demo composes existing SDK capabilities:
    - Capabilities discovery (keyhole_sdk.discovery)
    - Context retrieval (keyhole_sdk.context)
    - Proof scaffolding (keyhole_sdk.proof)

into a single coherent participant-side workflow that can be
demonstrated, repeated, and handed off to platform-side governance
when DEV-UX surfaces stabilize.

**Boundary posture: boundary-consuming.**

This module orchestrates participant-side actions only.
It does not define platform contract shapes, submit to undisclosed
endpoints, or claim proof submission is operational.
"""

from keyhole_sdk.demo.models import (
    DemoPhase,
    DemoResult,
    DemoStepResult,
)
from keyhole_sdk.demo.runner import DemoFlowRunner

__all__ = [
    "DemoFlowRunner",
    "DemoResult",
    "DemoPhase",
    "DemoStepResult",
]
