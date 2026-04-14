"""Governance explainability data models — SDK-CLIENT-20 §7-§10.

Models for explaining governed execution outcomes at the client boundary.

§3 Core Thesis: Explainability must preserve and present the lawful layers
of governed truth without inventing new ones. The client must distinguish
clearly between:

  Request truth   — what the client asked for, under which request identity
  Run truth       — whether a governed run exists, what state it reached
  Context truth   — what explicit governed context artifact was bound
  Event/proof     — what the platform emitted or referenced as lineage
  Rendered        — bounded human-readable explanation from those sources

§12.3: Distinguish known (server-returned) from inferred (client-side synthesis).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Outcome families (§9)
# ─────────────────────────────────────────────────────────────


class ExplainOutcomeClass(str, enum.Enum):
    """Outcome families the client can deterministically explain (§9).

    §20.19 forward-compatibility: renderers must support graceful fallback
    for unknown future values — see UNKNOWN.
    """

    ACCEPTED = "accepted"
    """Run submitted and accepted; not yet terminal."""

    SUCCEEDED = "succeeded"
    """Run reached a successful terminal state."""

    REJECTED = "rejected"
    """Run/request was rejected pre- or post-admission."""

    REPLAYED = "replayed"
    """Request did not create a new governed action — prior result reused."""

    DEFERRED = "deferred"
    """Platform deferred action; not a rejection, a governed pressure response."""

    RATE_LIMITED = "rate_limited"
    """Request constrained by rate or frequency policy."""

    BUDGET_EXHAUSTED = "budget_exhausted"
    """Run hit a runtime budget ceiling."""

    FAILED = "failed"
    """Run reached a terminal failure state."""

    PARTIAL_LINEAGE = "partial_lineage"
    """Some references exist; lineage still materializing or incomplete."""

    UNKNOWN = "unknown"
    """Cannot determine outcome class from available server truth."""


# §9 groups
_TERMINAL_CLASSES = frozenset({
    ExplainOutcomeClass.SUCCEEDED,
    ExplainOutcomeClass.REJECTED,
    ExplainOutcomeClass.FAILED,
    ExplainOutcomeClass.BUDGET_EXHAUSTED,
})

_NON_TERMINAL_CLASSES = frozenset({
    ExplainOutcomeClass.ACCEPTED,
    ExplainOutcomeClass.DEFERRED,
    ExplainOutcomeClass.RATE_LIMITED,
})

_PRESSURE_CLASSES = frozenset({
    ExplainOutcomeClass.DEFERRED,
    ExplainOutcomeClass.RATE_LIMITED,
    ExplainOutcomeClass.BUDGET_EXHAUSTED,
})


# ─────────────────────────────────────────────────────────────
# Run explanation (§8, §14)
# ─────────────────────────────────────────────────────────────


class RunExplanation(BaseModel):
    """Assembled, classified explanation for a governed run.

    §8: The explanation must include all 8 canonical sections:
      1. Summary
      2. Identity / Scope
      3. Request and Run Mapping
      4. Context Used
      5. Key Evidence
      6. Outcome
      7. Reason and Repair Guidance
      8. Proof / Support References

    §12.3: Fields labeled is_inferred=True were synthesized client-side
    from stable server metadata, not returned verbatim by the server.

    §12.1: Keep rendered output concise but complete for the builder's
    immediate question.
    """

    # ── Core identity (§8.2) ─────────────────────────────────
    run_id: str = Field("")
    request_id: str = Field("")
    correlation_id: str = Field("")
    outcome_class: ExplainOutcomeClass = Field(ExplainOutcomeClass.UNKNOWN)

    # ── Run truth (§8.3) ─────────────────────────────────────
    status: str = Field("")
    run_type: str = Field("")
    is_terminal: bool = Field(False)
    shadow: bool = Field(False)
    repo_name: str = Field("")

    # ── Context truth (§8.4) ─────────────────────────────────
    context_digest: str = Field("", description="Explicit governed context digest.")
    context_ref: str = Field("", description="Human-readable context reference.")

    # ── Reason (§9 — outcome-class-specific explanation text) ─
    reason: str = Field("", description="Server-returned or synthesized reason.")
    reason_code: str = Field("")
    is_reason_inferred: bool = Field(
        False,
        description="True when reason was synthesized from metadata, not returned verbatim.",
    )

    # ── Evidence (§8.5) ──────────────────────────────────────
    event_refs: List[str] = Field(default_factory=list)
    proof_refs: List[str] = Field(default_factory=list)
    proof_digest: str = Field("")

    # ── Budget surface (§20.19 — budget visibility inheritance) ─
    budget_summary: str = Field("")
    limit_outcome: str = Field("")

    # ── Replay (§9.3) ────────────────────────────────────────
    replayed_from: str = Field("", description="Prior run/request ID that was replayed.")
    idempotency_key: str = Field("")

    # ── Repair (§12.4) ───────────────────────────────────────
    repair_guidance: List[str] = Field(default_factory=list)

    # ── Summary text ─────────────────────────────────────────
    summary: str = Field("")

    # ── Partial lineage flag (§9 — honest lineage presentation) ─
    has_partial_lineage: bool = Field(False)
    lineage_note: str = Field("")

    # ── Raw and audit ────────────────────────────────────────
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    assembled_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_terminal_outcome(self) -> bool:
        """True if the outcome is a known terminal class."""
        return self.outcome_class in _TERMINAL_CLASSES

    def is_pressure(self) -> bool:
        """True if the outcome is a pressure outcome."""
        return self.outcome_class in _PRESSURE_CLASSES

    def to_proof_dict(self) -> Dict[str, Any]:
        """§14 minimum proof fields."""
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "outcome_class": self.outcome_class.value,
            "status": self.status,
            "run_type": self.run_type,
            "is_terminal": self.is_terminal,
            "shadow": self.shadow,
            "context_digest": self.context_digest,
            "reason": self.reason,
            "is_reason_inferred": self.is_reason_inferred,
            "event_refs": self.event_refs,
            "proof_refs": self.proof_refs,
            "repair_guidance": self.repair_guidance,
            "has_partial_lineage": self.has_partial_lineage,
            "assembled_at": self.assembled_at,
        }


# ─────────────────────────────────────────────────────────────
# Request inspection result (§7.2)
# ─────────────────────────────────────────────────────────────


class RequestInspectionResult(BaseModel):
    """Assembled inspection result for a governed request.

    Answers: what happened to this request?

    §7.2: Must surface: request identity, whether executions occurred,
    run linkage, context linkage, proof references, repair guidance.
    """

    # ── Request identity ─────────────────────────────────────
    request_id: str = Field("")
    correlation_id: str = Field("")
    idempotency_key: str = Field("")

    # ── Linked run (may be empty if no run was created) ──────
    run_id: str = Field("")
    outcome_class: ExplainOutcomeClass = Field(ExplainOutcomeClass.UNKNOWN)
    status: str = Field("")

    # ── Disposition flags ────────────────────────────────────
    executed: bool = Field(False, description="Whether a run was created and dispatched.")
    replayed: bool = Field(False, description="Whether the server reused a prior result.")
    deferred: bool = Field(False, description="Whether the action was deferred.")

    # ── Context ──────────────────────────────────────────────
    context_ref: str = Field("")

    # ── Evidence ─────────────────────────────────────────────
    event_refs: List[str] = Field(default_factory=list)
    proof_refs: List[str] = Field(default_factory=list)

    # ── Reason / repair ──────────────────────────────────────
    reason: str = Field("")
    repair_guidance: List[str] = Field(default_factory=list)

    # ── Raw and audit ────────────────────────────────────────
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    assembled_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "outcome_class": self.outcome_class.value,
            "status": self.status,
            "executed": self.executed,
            "replayed": self.replayed,
            "deferred": self.deferred,
            "reason": self.reason,
            "repair_guidance": self.repair_guidance,
            "assembled_at": self.assembled_at,
        }


# ─────────────────────────────────────────────────────────────
# Support bundle (§10)
# ─────────────────────────────────────────────────────────────

# Required section keys per §10
BUNDLE_REQUIRED_SECTIONS = (
    "summary_md",
    "request",
    "run",
    "context",
    "events",
    "proof_refs",
    "outcome",
    "repair",
    "metadata",
)


class SupportBundle(BaseModel):
    """Portable, bounded support artifact for governed execution.

    §10: Must be deterministic, portable, bounded, and free of secrets.
    If some sections are unavailable, an explicit omission note is included.

    Default on-disk layout per §14:
      support_bundle/<run-id-or-request-id>/
        summary.md
        request.json
        run.json
        context.json
        events.json
        proof_refs.json
        outcome.json
        repair.json
        metadata.json
    """

    # ── Identity ─────────────────────────────────────────────
    run_id: str = Field("")
    request_id: str = Field("")

    # ── Sections: present sections ───────────────────────────
    summary_md: str = Field("")
    request: Dict[str, Any] = Field(default_factory=dict)
    run: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    events: Dict[str, Any] = Field(default_factory=dict)
    proof_refs: Dict[str, Any] = Field(default_factory=dict)
    outcome: Dict[str, Any] = Field(default_factory=dict)
    repair: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ── Omissions ────────────────────────────────────────────
    missing_sections: List[str] = Field(
        default_factory=list,
        description="Sections not available — populated with explicit omission note.",
    )
    omission_notes: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-section omission reason.",
    )

    # ── Audit ─────────────────────────────────────────────────
    cli_version: str = Field("0.2.0")
    assembled_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_files_dict(self) -> Dict[str, Any]:
        """Produce a mapping of filename → content for writing to disk.

        §10: Missing sections produce an omission object rather than
        silently skipping the file.
        """
        files: Dict[str, Any] = {
            "summary.md": self.summary_md or _omission_md(
                "summary", self.omission_notes.get("summary_md", "Not available.")
            ),
            "request.json": self.request or _omission_obj("request", self.omission_notes),
            "run.json": self.run or _omission_obj("run", self.omission_notes),
            "context.json": self.context or _omission_obj("context", self.omission_notes),
            "events.json": self.events or _omission_obj("events", self.omission_notes),
            "proof_refs.json": self.proof_refs or _omission_obj("proof_refs", self.omission_notes),
            "outcome.json": self.outcome or _omission_obj("outcome", self.omission_notes),
            "repair.json": self.repair or _omission_obj("repair", self.omission_notes),
            "metadata.json": self.metadata or _omission_obj("metadata", self.omission_notes),
        }
        return files


def _omission_md(section: str, reason: str) -> str:
    return f"# {section.replace('_', ' ').title()}\n\n**Omission note:** {reason}\n"


def _omission_obj(key: str, notes: Dict[str, str]) -> Dict[str, Any]:
    reason = notes.get(key, "Not available at bundle assembly time.")
    return {"omission": True, "section": key, "reason": reason}
