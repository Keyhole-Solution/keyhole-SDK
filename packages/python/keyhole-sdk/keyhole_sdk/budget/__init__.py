"""Budget, limit, and overload visibility — SDK-CLIENT-19.

Turns runtime pressure into part of the product experience.

Makes existing server-side budget and overload behavior usable at
the client boundary: deterministic rendering, proof emission, and
repair-oriented next actions.

Public exports (10 symbols):
  LimitOutcomeClass      — outcome family enum
  BudgetSnapshot         — single budget dimension fields
  LimitResult            — full parsed limit/budget outcome
  BudgetPressureRequest  — request metadata for proof
  parse_limit_outcome    — parse server response → LimitResult
  render_budget_summary  — deterministic human-readable rendering
  emit_budget_proof      — write proof artifacts to tool-owned state dir
  map_budget_repair      — concrete repair guidance by outcome class
  is_pressure_outcome    — quick predicate for overload classification
  classify_retry_posture — should the caller retry, wait, or stop?
"""

from keyhole_sdk.budget.models import (
    LimitOutcomeClass,
    BudgetSnapshot,
    LimitResult,
    BudgetPressureRequest,
)
from keyhole_sdk.budget.parser import parse_limit_outcome
from keyhole_sdk.budget.renderer import render_budget_summary
from keyhole_sdk.budget.proof import emit_budget_proof
from keyhole_sdk.budget.repair import map_budget_repair
from keyhole_sdk.budget.classifier import is_pressure_outcome, classify_retry_posture

__all__ = [
    "LimitOutcomeClass",
    "BudgetSnapshot",
    "LimitResult",
    "BudgetPressureRequest",
    "parse_limit_outcome",
    "render_budget_summary",
    "emit_budget_proof",
    "map_budget_repair",
    "is_pressure_outcome",
    "classify_retry_posture",
]
