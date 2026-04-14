"""Alignment guidance data models — SDK-CLIENT-11.

Covers:
  GuidanceClass     — gap / warning / suggestion / next_best_action / inference
  GuidanceSeverity  — high / medium / low / info
  GuidanceState     — verified / inferred
  AlignmentReadiness— foreign / partially_aligned / registration_ready /
                      run_ready / blocked
  GuidanceItem      — a single ranked guidance record
  AlignmentGuidanceRequest — input to the guidance surface
  AlignmentGuidanceResult  — full output including rendered items, posture,
                              next-best action, proof refs

All models use Pydantic v2.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class GuidanceClass(str, enum.Enum):
    """§7: Semantic class of a guidance item."""
    GAP = "gap"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NEXT_BEST_ACTION = "next_best_action"
    INFERENCE = "inference"


class GuidanceSeverity(str, enum.Enum):
    """Severity of a guidance item for ordering purposes."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GuidanceState(str, enum.Enum):
    """§3, §7: Whether a finding is deterministically verified or inferred (graph-derived)."""
    VERIFIED = "verified"
    INFERRED = "inferred"


class AlignmentReadiness(str, enum.Enum):
    """§10: Top-level alignment posture summary."""
    FOREIGN = "foreign"
    PARTIALLY_ALIGNED = "partially_aligned"
    REGISTRATION_READY = "registration_ready"
    RUN_READY = "run_ready"
    BLOCKED = "blocked"


# ── Severity ordering (lower = higher priority) ───────────

_SEVERITY_ORDER: Dict[str, int] = {
    GuidanceSeverity.HIGH: 0,
    GuidanceSeverity.MEDIUM: 1,
    GuidanceSeverity.LOW: 2,
    GuidanceSeverity.INFO: 3,
}

_STATE_ORDER: Dict[str, int] = {
    GuidanceState.VERIFIED: 0,
    GuidanceState.INFERRED: 1,
}

_CLASS_ORDER: Dict[str, int] = {
    GuidanceClass.GAP: 0,
    GuidanceClass.WARNING: 1,
    GuidanceClass.SUGGESTION: 2,
    GuidanceClass.NEXT_BEST_ACTION: 3,
    GuidanceClass.INFERENCE: 4,
}


# ── Core Model ────────────────────────────────────────────


class GuidanceItem(BaseModel):
    """§7: A single ranked guidance record.

    Required fields per §7:
      id, class, severity, confidence, state, title, detail, repair, source
    """

    id: str = Field(..., description="Stable canonical ID, e.g. 'gap.contract.missing_provider_pin'.")
    guidance_class: GuidanceClass = Field(
        ..., alias="class", description="Guidance category."
    )
    severity: GuidanceSeverity = Field(GuidanceSeverity.MEDIUM)
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0–1.0) for inferred items.",
    )
    state: GuidanceState = Field(GuidanceState.VERIFIED)
    title: str = Field(..., description="Short, scan-safe title.")
    detail: str = Field("", description="Full guidance detail.")
    repair: List[str] = Field(
        default_factory=list,
        description="Ordered list of concrete repair steps.",
    )
    source: str = Field("", description="Source surface that produced this item.")
    artifact_ref: str = Field("", description="Optional reference to a proof artifact.")

    model_config = {"populate_by_name": True}

    def sort_key(self) -> tuple:
        """Deterministic sort key per §9 precedence rules.

        Primary: class (gap first)
        Secondary: state (verified before inferred)
        Tertiary: severity (high before low)
        Quaternary: confidence desc (higher confidence first)
        Quinary: canonical id (alphabetical)
        """
        return (
            _CLASS_ORDER.get(self.guidance_class, 99),
            _STATE_ORDER.get(self.state, 99),
            _SEVERITY_ORDER.get(self.severity, 99),
            -self.confidence,
            self.id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "class": self.guidance_class.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "state": self.state.value,
            "title": self.title,
            "detail": self.detail,
            "repair": self.repair,
            "source": self.source,
            "artifact_ref": self.artifact_ref,
        }


# ── Request / Result ──────────────────────────────────────


class AlignmentGuidanceRequest(BaseModel):
    """Input to the alignment guidance surface."""

    repo_identity: str = Field("", description="Repo name or path identity.")
    repo_path: str = Field("", description="Absolute local path to the repo.")
    analysis_id: str = Field("", description="Analysis ID from a prior ingestion or run.")
    ingestion_outcome: Optional[Dict[str, Any]] = Field(
        None, description="Serialized ingestion outcome for local rendering."
    )
    guidance_items: List[GuidanceItem] = Field(
        default_factory=list,
        description="Pre-loaded guidance items (used for local rendering without MCP).",
    )
    shadow: bool = Field(False, description="Advisory/shadow mode — no repo mutation.")
    correlation_id: str = Field("")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_payload(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "repo_identity": self.repo_identity,
            "analysis_id": self.analysis_id,
            "shadow": self.shadow,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }
        if self.ingestion_outcome:
            d["ingestion_outcome"] = self.ingestion_outcome
        return d

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "repo_identity": self.repo_identity,
            "analysis_id": self.analysis_id,
            "shadow": self.shadow,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "guidance_items_count": len(self.guidance_items),
        }


class AlignmentGuidanceResult(BaseModel):
    """Output from the alignment guidance surface.

    Honest rendering of guidance, posture, next-best action, and proof refs.
    Explicitly preserves verified vs inferred layering.
    """

    success: bool = Field(True)
    readiness: AlignmentReadiness = Field(AlignmentReadiness.FOREIGN)
    items: List[GuidanceItem] = Field(default_factory=list)
    next_best_action: Optional[str] = Field(None)
    verified_count: int = Field(0)
    inferred_count: int = Field(0)
    gap_count: int = Field(0)
    warning_count: int = Field(0)
    suggestion_count: int = Field(0)
    no_mutation_applied: bool = Field(True, description="Proof that no repo mutation occurred.")
    correlation_id: str = Field("")
    run_id: Optional[str] = Field(None)
    analysis_mode: str = Field("terminal", description="'terminal', 'accepted', or 'deferred'.")
    error_class: str = Field("")
    reason: str = Field("")
    repair_guidance: List[str] = Field(default_factory=list)

    def is_accepted_or_deferred(self) -> bool:
        return self.analysis_mode in ("accepted", "deferred")

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "readiness": self.readiness.value,
            "verified_count": self.verified_count,
            "inferred_count": self.inferred_count,
            "gap_count": self.gap_count,
            "warning_count": self.warning_count,
            "suggestion_count": self.suggestion_count,
            "no_mutation_applied": self.no_mutation_applied,
            "analysis_mode": self.analysis_mode,
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "next_best_action": self.next_best_action,
            "item_count": len(self.items),
        }
