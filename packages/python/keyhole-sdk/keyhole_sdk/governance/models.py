"""Governance proof protocol models.

CE-V5 — Recursive Governance Proof Test (RG-01).

Models for the cross-boundary participant validation protocol that
proves an external SDK repository can:
    - inherit governance context
    - perform work independently
    - submit proof
    - receive a deterministic verdict
    - affect canonical state

while remaining separate from the platform repository.

**Phases 1, 5, 6, 7 are SCAFFOLDED** — they depend on platform-side
surfaces (DEV-UX) that are not yet stable.

**Phases 2, 3, 4 are SUPPORTED** — they use existing SDK surfaces
(context retrieval, local implementation capture, local verification).

Must never:
    - claim scaffolded phases are operational
    - hardcode unstable platform endpoints
    - couple to private platform source
    - fabricate Event Spine evidence from local-only runs
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from keyhole_sdk.proof.models import (
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)


# ──────────────────────────────────────────────────────────────
# Governance Phase Enum
# ──────────────────────────────────────────────────────────────

class GovernancePhase(str, Enum):
    """Ordered phases of the RG-01 cross-boundary governance proof.

    Each phase produces an expected Event Spine event when operating
    against a live governed boundary.
    """

    REGISTRATION = "registration"
    """Phase 1 — Participant contract registration."""

    CONTEXT = "context"
    """Phase 2 — Context inheritance via context.compile."""

    IMPLEMENTATION = "implementation"
    """Phase 3 — External implementation (local commit capture)."""

    VERIFICATION = "verification"
    """Phase 4 — Local verification execution."""

    SUBMISSION = "submission"
    """Phase 5 — Proof bundle submission."""

    EVALUATION = "evaluation"
    """Phase 6 — Governance verdict evaluation."""

    PROMOTION = "promotion"
    """Phase 7 — Promotion execution (optional but ideal)."""


# ──────────────────────────────────────────────────────────────
# Expected Event Spine Events
# ──────────────────────────────────────────────────────────────

EXPECTED_EVENTS: Dict[GovernancePhase, str] = {
    GovernancePhase.REGISTRATION: "participant.contract.registered",
    GovernancePhase.CONTEXT: "context.compile.resolved",
    GovernancePhase.IMPLEMENTATION: "implementation.commit.captured",
    GovernancePhase.SUBMISSION: "proof.bundle.submitted",
    GovernancePhase.EVALUATION: "governance.verdict",
    GovernancePhase.PROMOTION: "promotion.executed",
}
"""Mapping of phases to their expected Event Spine event names."""


# ──────────────────────────────────────────────────────────────
# Governance Event
# ──────────────────────────────────────────────────────────────

class GovernanceEvent(BaseModel):
    """Represents a single Event Spine event in the governance trace.

    Each event records what happened at a specific governance phase.
    In local-only mode, events are assembled locally without claiming
    upstream auditability.
    """

    event_type: str = Field(
        description="Event Spine event type (e.g., 'participant.contract.registered').",
    )
    phase: GovernancePhase = Field(
        description="Governance phase that produced this event.",
    )
    participant_id: str = Field(
        default="keyhole-developer-kit",
        description="Participant that produced the event.",
    )
    correlation_id: str = Field(
        default="",
        description="Shared correlation ID across the governance trace.",
    )
    event_digest: str = Field(
        default="",
        description="Content digest of this event.",
    )
    contract_digest: str = Field(
        default="",
        description="Digest of the participant contract.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this event was recorded.",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Phase-specific event payload.",
    )
    scaffolded: bool = Field(
        default=False,
        description="True if this event is from a scaffolded phase.",
    )


# ──────────────────────────────────────────────────────────────
# Phase Result
# ──────────────────────────────────────────────────────────────

class GovernancePhaseResult(BaseModel):
    """Result of executing one governance phase."""

    phase: GovernancePhase
    success: bool = False
    scaffolded: bool = Field(
        default=False,
        description="True if the phase is scaffolded (not yet live).",
    )
    event: Optional[GovernanceEvent] = Field(
        default=None,
        description="Event produced by this phase, if any.",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Phase-specific result data.",
    )
    error: str = ""
    suggestion: str = ""


# ──────────────────────────────────────────────────────────────
# Governance Proof Result
# ──────────────────────────────────────────────────────────────

class GovernanceProofResult(BaseModel):
    """Aggregate result of the RG-01 governance proof protocol.

    Contains results for all 7 phases and the assembled evidence.
    """

    test_id: str = Field(
        default="RG-01",
        description="Test protocol identifier.",
    )
    participant: str = Field(
        default="keyhole-developer-kit",
        description="Participant executing the test.",
    )
    phases: List[GovernancePhaseResult] = Field(
        default_factory=list,
        description="Results for each governance phase.",
    )
    proof_bundle: Optional[ProofBundlePlaceholder] = Field(
        default=None,
        description="Proof bundle assembled in Phase 4.",
    )
    correlation_id: str = Field(
        default="",
        description="Shared correlation ID across all phases.",
    )
    support_status: SupportStatus = Field(
        default=SupportStatus.SCAFFOLDED,
        description="Overall support status of the protocol.",
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def all_supported_passed(self) -> bool:
        """True if all non-scaffolded phases succeeded."""
        return all(
            p.success for p in self.phases if not p.scaffolded
        )

    @property
    def all_passed(self) -> bool:
        """True if all phases (including scaffolded) succeeded."""
        return all(p.success for p in self.phases)

    @property
    def events(self) -> List[str]:
        """Event type names from all phases that produced events."""
        return [
            p.event.event_type
            for p in self.phases
            if p.event is not None
        ]

    @property
    def phase_summary(self) -> Dict[str, Any]:
        """Summary of phase results."""
        total = len(self.phases)
        passed = sum(1 for p in self.phases if p.success)
        scaffolded = sum(1 for p in self.phases if p.scaffolded)
        supported_passed = sum(
            1 for p in self.phases if p.success and not p.scaffolded
        )
        supported_total = total - scaffolded
        return {
            "total_phases": total,
            "passed": passed,
            "failed": total - passed,
            "scaffolded": scaffolded,
            "supported_passed": supported_passed,
            "supported_total": supported_total,
            "all_supported_passed": self.all_supported_passed,
        }

    def get_phase(self, phase: GovernancePhase) -> GovernancePhaseResult:
        """Get the result for a specific phase."""
        for p in self.phases:
            if p.phase == phase:
                return p
        return GovernancePhaseResult(
            phase=phase,
            error="Phase not executed",
        )

    def to_evidence_bundle(self) -> Dict[str, Any]:
        """Produce the recursive-governance-proof.json artifact."""
        has_scaffolded = any(p.scaffolded for p in self.phases)
        if not any(p.success for p in self.phases):
            result = "FAILURE"
        elif has_scaffolded:
            result = "PARTIAL"
        elif self.all_supported_passed:
            result = "SUCCESS"
        else:
            result = "PARTIAL"

        return {
            "test_id": self.test_id,
            "participant": self.participant,
            "events": self.events,
            "correlation_id": self.correlation_id,
            "result": result,
            "phase_summary": self.phase_summary,
            "scaffolded_phases": [
                p.phase.value for p in self.phases if p.scaffolded
            ],
            "supported_phases": [
                p.phase.value for p in self.phases if not p.scaffolded
            ],
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
        }

    def summary(self) -> str:
        """Human-readable summary of the governance proof result."""
        lines = [
            f"=== Recursive Governance Proof — {self.test_id} ===",
            f"Participant: {self.participant}",
            f"Correlation: {self.correlation_id or '(local)'}",
            "",
        ]

        for p in self.phases:
            status = "PASS" if p.success else "SKIP" if p.scaffolded else "FAIL"
            scaffold_marker = " [scaffolded]" if p.scaffolded else ""
            lines.append(
                f"  Phase {p.phase.value:<16s} {status}{scaffold_marker}"
            )
            if p.error:
                lines.append(f"    error: {p.error}")

        ps = self.phase_summary
        lines.append("")
        lines.append(
            f"Supported: {ps['supported_passed']}/{ps['supported_total']} passed"
        )
        lines.append(f"Scaffolded: {ps['scaffolded']} phases awaiting platform surfaces")

        verdict = "LAUNCH-READY" if self.all_supported_passed else "NOT READY"
        lines.append(f"Verdict: {verdict}")

        return "\n".join(lines)
