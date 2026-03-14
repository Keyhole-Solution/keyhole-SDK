"""Models for the recursive demo flow.

CE-V5-S42-09: Recursive Demo Readiness Pack.

Defines structured result types for each phase of the demo flow
so consumers can inspect success/failure and evidence clearly.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from keyhole_sdk.proof.models import (
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)


class DemoPhase(str, Enum):
    """Named phases in the recursive demo flow.

    Ordered to match the canonical demo execution sequence.
    """

    DISCOVERY = "discovery"
    """Boundary capabilities retrieval (unauthenticated)."""

    IDENTITY = "identity"
    """Participant identity inspection (authenticated)."""

    CONTEXT = "context"
    """Governed context retrieval via context.compile."""

    POSTURE = "posture"
    """Participant contract posture confirmation."""

    VERIFICATION = "verification"
    """Local verification execution and result collection."""

    BUNDLE = "bundle"
    """Proof bundle assembly from verification outputs."""

    HANDOFF = "handoff"
    """Proof handoff attempt to platform (scaffolded)."""


class DemoStepResult(BaseModel):
    """Result of one demo flow phase.

    ``success`` is True when the phase completed without error.
    ``scaffolded`` is True when the phase is a placeholder awaiting
    DEV-UX surface stabilization.
    ``data`` contains phase-specific structured information.
    """

    phase: DemoPhase
    success: bool = False
    scaffolded: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    suggestion: str = ""


class DemoResult(BaseModel):
    """Aggregate result of the full recursive demo flow.

    Contains one :class:`DemoStepResult` per executed phase.
    Includes the assembled proof bundle and verification outputs.
    """

    steps: List[DemoStepResult] = Field(default_factory=list)
    verification_outputs: List[VerificationOutput] = Field(default_factory=list)
    proof_bundle: Optional[ProofBundlePlaceholder] = None
    support_status: SupportStatus = SupportStatus.SCAFFOLDED

    @property
    def all_passed(self) -> bool:
        """True if all non-scaffolded steps succeeded."""
        executed = [s for s in self.steps if not s.scaffolded]
        return len(executed) > 0 and all(s.success for s in executed)

    @property
    def verification_summary(self) -> Dict[str, Any]:
        """Summary of verification results."""
        total = len(self.verification_outputs)
        passed = sum(1 for v in self.verification_outputs if v.passed)
        return {
            "total_verifications": total,
            "passed": passed,
            "failed": total - passed,
        }

    def get_step(self, phase: DemoPhase) -> DemoStepResult:
        """Return the result for a specific phase, or a not-executed stub."""
        for s in self.steps:
            if s.phase == phase:
                return s
        return DemoStepResult(
            phase=phase,
            error="Phase was not executed.",
        )

    def summary(self) -> str:
        """Human-readable summary of the demo flow."""
        lines = ["Recursive Demo Flow Results", "=" * 40]
        for s in self.steps:
            if s.scaffolded:
                status = "SCAFFOLDED"
            elif s.success:
                status = "PASS"
            else:
                status = "FAIL"
            lines.append(f"  [{status}] {s.phase.value}")
            if s.error:
                lines.append(f"         Error: {s.error}")
            if s.suggestion:
                lines.append(f"         Suggestion: {s.suggestion}")
        lines.append("=" * 40)
        if self.all_passed:
            lines.append("  ALL EXECUTABLE PHASES PASSED")
        else:
            lines.append("  DEMO FLOW INCOMPLETE")
        lines.append(f"  Verification: {self.verification_summary}")
        return "\n".join(lines)
