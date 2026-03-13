"""Models for the read-only smoke path.

CE-V5-S42-07: Read-Only Smoke Path.

Defines structured result types for each phase of the smoke path
so consumers can inspect success/failure clearly.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class SmokePhase(str, Enum):
    """Named phases in the read-only smoke path."""

    DISCOVERY = "discovery"
    IDENTITY = "identity"
    CONTEXT = "context"
    READONLY_RUN = "readonly_run"


class PhaseResult(BaseModel):
    """Result of one smoke-path phase.

    ``success`` is True only when the phase completed without error.
    ``data`` contains phase-specific summary information.
    ``error`` contains the failure description when ``success`` is False.
    """

    phase: SmokePhase
    success: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    suggestion: str = ""


class SmokeResult(BaseModel):
    """Aggregate result of the full read-only smoke path.

    Contains one :class:`PhaseResult` per phase, in execution order.
    ``all_passed`` is True only when every phase succeeded.
    """

    phases: List[PhaseResult] = Field(default_factory=list)
    read_only: bool = True

    @property
    def all_passed(self) -> bool:
        return len(self.phases) > 0 and all(p.success for p in self.phases)

    def get_phase(self, phase: SmokePhase) -> PhaseResult:
        """Return the result for a specific phase, or a failed stub."""
        for p in self.phases:
            if p.phase == phase:
                return p
        return PhaseResult(
            phase=phase,
            success=False,
            error="Phase was not executed.",
        )

    def summary(self) -> str:
        """Human-readable summary of the smoke path."""
        lines = ["Read-Only Smoke Path Results", "=" * 40]
        for p in self.phases:
            status = "PASS" if p.success else "FAIL"
            lines.append(f"  [{status}] {p.phase.value}")
            if p.error:
                lines.append(f"         Error: {p.error}")
            if p.suggestion:
                lines.append(f"         Suggestion: {p.suggestion}")
        lines.append("=" * 40)
        verdict = "ALL PHASES PASSED" if self.all_passed else "SMOKE PATH INCOMPLETE"
        lines.append(f"  {verdict}")
        lines.append(f"  Read-only: {self.read_only}")
        return "\n".join(lines)
