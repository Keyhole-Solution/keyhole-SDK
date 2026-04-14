"""Budget, limit, and overload visibility models — SDK-CLIENT-19 §7, §9, §14.

Structural models for all categories of runtime pressure:
  - success with budget visibility (§7.1)
  - deferred / temporarily held (§7.2)
  - rate limited / concurrency limited (§7.3)
  - budget exhausted in-run (§7.4)
  - unknown or future pressure categories (§7.5)

§19 forward-compatibility: LimitResult carries optional structured
metadata and a stable top-level outcome class, so future budget
categories can be added without redesigning the client model.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Outcome family enum
# ─────────────────────────────────────────────────────────────


class LimitOutcomeClass(str, enum.Enum):
    """Families of runtime pressure outcomes (§7).

    § Forward-compatibility: Renderers must support fallback for
    future values not listed here. Use the 'unknown_pressure' fallback.
    """

    SUCCESS_WITH_BUDGET_VISIBILITY = "success_with_budget_visibility"
    """Run completed. Server returned budget posture or near-limit info."""

    BUDGET_EXHAUSTED = "budget_exhausted"
    """Run started lawfully but hit a runtime budget ceiling (§7.4)."""

    DEFERRED = "deferred"
    """Request not arbitrarily rejected — governed pressure handling (§7.2)."""

    RATE_LIMITED = "rate_limited"
    """Request constrained by rate or concurrency policy (§7.3)."""

    CONCURRENCY_LIMITED = "concurrency_limited"
    """Request gated by concurrency slot availability (§7.3)."""

    UNKNOWN_PRESSURE = "unknown_pressure"
    """Unknown or future limit class — graceful fallback (§7.5)."""

    NO_PRESSURE_DATA = "no_pressure_data"
    """Response carried no budget or limit metadata."""


# §8.1 map: which outcomes are temporary (retry might help)?
_TEMPORARY_OUTCOMES = frozenset({
    LimitOutcomeClass.DEFERRED,
    LimitOutcomeClass.RATE_LIMITED,
    LimitOutcomeClass.CONCURRENCY_LIMITED,
})

# §8.1 map: which outcomes are hard-terminal (retry unchanged won't help)?
_HARD_TERMINAL_OUTCOMES = frozenset({
    LimitOutcomeClass.BUDGET_EXHAUSTED,
})


# ─────────────────────────────────────────────────────────────
# Budget snapshot (single dimension — §9)
# ─────────────────────────────────────────────────────────────


class BudgetSnapshot(BaseModel):
    """One runtime budget dimension as reported by the server (§9).

    The client must not invent budget classes or values the server
    did not provide (§15 prohibition).

    Example budget classes: wall_time, event, memory, byte, concurrency_slot
    """

    budget_class: str = Field("", description="Budget category (server-supplied).")
    budget_used: Optional[float] = Field(None, description="Amount consumed so far.")
    budget_remaining: Optional[float] = Field(None, description="Amount still available.")
    budget_unit: str = Field("", description="Unit of measurement (e.g. 'ms', 'events').")
    near_limit: bool = Field(False, description="Server signalled near-limit condition.")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_class": self.budget_class,
            "budget_used": self.budget_used,
            "budget_remaining": self.budget_remaining,
            "budget_unit": self.budget_unit,
            "near_limit": self.near_limit,
            "retry_after": self.retry_after,
        }


# ─────────────────────────────────────────────────────────────
# Full limit result — what the client surfaces (§7, §14.2)
# ─────────────────────────────────────────────────────────────


class LimitResult(BaseModel):
    """Parsed, classified limit/budget outcome for client rendering.

    § Forward-compatibility guarantee: treat outcome_class as a stable
    top-level category; metadata fields are all optional so future
    limit categories degrade gracefully.

    § §14.2 minimum proof fields: run_id, request_id, status,
    limit_outcome, limit_class, budget_snapshot, retry_after,
    repair_guidance, correlation_id.
    """

    # Core classification
    outcome_class: LimitOutcomeClass = Field(LimitOutcomeClass.NO_PRESSURE_DATA)
    run_id: str = Field("")
    request_id: str = Field("")
    status: str = Field("")

    # Limit metadata (§9 — optional structured fields)
    limit_class: str = Field("", description="Server-supplied limit class string.")
    budget_snapshots: List[BudgetSnapshot] = Field(
        default_factory=list,
        description="Budget dimensions reported by the server.",
    )
    partial_execution: bool = Field(
        False,
        description="Whether the run began before hitting the limit.",
    )
    is_terminal: bool = Field(True)
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry.")
    retry_safe: bool = Field(
        False,
        description="Whether retrying unchanged is likely to succeed.",
    )

    # Proof and repair
    repair_guidance: List[str] = Field(default_factory=list)
    correlation_id: str = Field("")
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved server response for proof.",
    )
    parsed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_pressure(self) -> bool:
        """True if the outcome represents any form of runtime pressure."""
        return self.outcome_class not in (
            LimitOutcomeClass.SUCCESS_WITH_BUDGET_VISIBILITY,
            LimitOutcomeClass.NO_PRESSURE_DATA,
        )

    def is_retryable(self) -> bool:
        """True if the caller could benefit from retrying later (§8.1)."""
        return self.outcome_class in _TEMPORARY_OUTCOMES or self.retry_safe

    def is_hard_terminal(self) -> bool:
        """True if retrying unchanged is unlikely to help (§8.1)."""
        return self.outcome_class in _HARD_TERMINAL_OUTCOMES and not self.retry_safe

    def to_proof_dict(self) -> Dict[str, Any]:
        """Minimum required proof fields per §14.2."""
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "status": self.status,
            "limit_outcome": self.outcome_class.value,
            "limit_class": self.limit_class,
            "budget_snapshot": [s.to_dict() for s in self.budget_snapshots],
            "retry_after": self.retry_after,
            "repair_guidance": self.repair_guidance,
            "correlation_id": self.correlation_id,
            "partial_execution": self.partial_execution,
            "is_terminal": self.is_terminal,
            "retry_safe": self.retry_safe,
            "parsed_at": self.parsed_at,
        }


# ─────────────────────────────────────────────────────────────
# Request metadata for proof binding (§14)
# ─────────────────────────────────────────────────────────────


class BudgetPressureRequest(BaseModel):
    """Metadata captured when inspecting budget posture for a run."""

    run_id: str = Field("")
    request_id: str = Field("")
    correlation_id: str = Field("")
    mcp_url: str = Field("")
    queried_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
