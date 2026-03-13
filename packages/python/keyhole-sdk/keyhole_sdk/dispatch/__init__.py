"""Run-type safety and dispatch preflight.

CE-V5-S42-06: Run-Type Safety & Schema Discovery Helpers.

Public API for validating run types, discovering request schemas,
and performing preflight checks before dispatch.
"""

from keyhole_sdk.dispatch.models import (
    ErrorRecoveryGuidance,
    PreflightResult,
    PreflightStatus,
    RecoveryAction,
    RunTypeCheckResult,
    RunTypeStatus,
    SchemaHint,
)
from keyhole_sdk.dispatch.preflight import DispatchPreflight
from keyhole_sdk.dispatch.schema import SchemaHelper
from keyhole_sdk.dispatch.validator import (
    CANONICAL_RUN_TYPES,
    KNOWN_MISTAKES,
    RunTypeValidator,
)

__all__ = [
    # Validator
    "RunTypeValidator",
    "CANONICAL_RUN_TYPES",
    "KNOWN_MISTAKES",
    # Schema
    "SchemaHelper",
    # Preflight
    "DispatchPreflight",
    # Models
    "RunTypeCheckResult",
    "RunTypeStatus",
    "SchemaHint",
    "PreflightResult",
    "PreflightStatus",
    "ErrorRecoveryGuidance",
    "RecoveryAction",
]
