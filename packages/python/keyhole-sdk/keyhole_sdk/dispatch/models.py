"""Models for run-type safety, schema discovery, and dispatch preflight.

CE-V5-S42-06: Run-Type Safety & Schema Discovery Helpers.

Defines the output shapes for run-type validation, schema hints,
preflight checks, and error recovery guidance.  These models are
participant-side artifacts — they do not represent server responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# A) Run-Type Check Result
# ──────────────────────────────────────────────────────────────

class RunTypeStatus(str, Enum):
    """Status of a run-type validation check."""

    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class RunTypeCheckResult(BaseModel):
    """Result of validating an intended run type against known guidance.

    A ``valid`` result means the run type matches a known canonical key.
    An ``invalid`` result means it matches a known-bad form with
    suggestions.  An ``unknown`` result means it is not recognized at
    all — the participant should re-discover before dispatch.
    """

    run_type: str = ""
    status: RunTypeStatus = RunTypeStatus.UNKNOWN
    suggestions: List[str] = Field(default_factory=list)
    reason: str = ""

    @property
    def is_valid(self) -> bool:
        return self.status == RunTypeStatus.VALID

    @property
    def is_invalid(self) -> bool:
        return self.status == RunTypeStatus.INVALID


# ──────────────────────────────────────────────────────────────
# B) Schema Hint
# ──────────────────────────────────────────────────────────────

class SchemaHint(BaseModel):
    """Schema or request-shape guidance for a known run type.

    When ``available`` is False, the participant should re-discover
    schema before assuming request shape.
    """

    run_type: str = ""
    available: bool = False
    required_params: List[str] = Field(default_factory=list)
    optional_params: List[str] = Field(default_factory=list)
    example: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


# ──────────────────────────────────────────────────────────────
# C) Preflight Result
# ──────────────────────────────────────────────────────────────

class PreflightStatus(str, Enum):
    """Status of a dispatch preflight check."""

    PASS = "pass"
    WARN = "warn"
    REJECT = "reject"


class PreflightResult(BaseModel):
    """Result of a dispatch preflight check.

    Communicates whether the intended dispatch should proceed,
    proceed with warnings, or be rejected before reaching the
    boundary.
    """

    status: PreflightStatus = PreflightStatus.REJECT
    run_type: str = ""
    reason: str = ""
    suggested_next_step: str = ""
    warnings: List[str] = Field(default_factory=list)

    @property
    def should_proceed(self) -> bool:
        return self.status in (PreflightStatus.PASS, PreflightStatus.WARN)


# ──────────────────────────────────────────────────────────────
# D) Error Recovery Guidance
# ──────────────────────────────────────────────────────────────

class RecoveryAction(BaseModel):
    """A single recovery action for the participant to consider."""

    action: str = ""
    detail: str = ""


class ErrorRecoveryGuidance(BaseModel):
    """Recovery guidance when a run type or request shape is rejected.

    Tells the participant what went wrong and what to do next.
    """

    error_class: str = ""
    run_type: str = ""
    message: str = ""
    actions: List[RecoveryAction] = Field(default_factory=list)

    def action_summary(self) -> List[str]:
        """Return a list of action strings for display."""
        return [a.action for a in self.actions]
