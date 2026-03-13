"""Dispatch preflight checks.

CE-V5-S42-06: Run-Type Safety & Schema Discovery Helpers.

Composes run-type validation and schema checking into a single
preflight gate that participants use before dispatch.

The preflight check determines whether a dispatch should:
  - proceed (pass)
  - proceed with warnings (warn)
  - be rejected before reaching the boundary (reject)

Must never:
  - silently fix invalid dispatch names
  - fabricate support for unknown run types
  - replace server-side validation
  - depend on private platform source
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.dispatch.models import (
    ErrorRecoveryGuidance,
    PreflightResult,
    PreflightStatus,
    RecoveryAction,
    RunTypeStatus,
)
from keyhole_sdk.dispatch.schema import SchemaHelper
from keyhole_sdk.dispatch.validator import RunTypeValidator


class DispatchPreflight:
    """Participant-side preflight check before run dispatch.

    Validates the run type and request parameters before the request
    reaches the MCP boundary.  Prevents the most common invalid
    dispatch patterns:
      - guessed / pluralized run-type names
      - missing required parameters
      - dispatch without prior discovery

    Usage::

        preflight = DispatchPreflight()
        result = preflight.check("gaps.states")
        assert result.status == PreflightStatus.REJECT
        print(result.reason)

    With capabilities::

        caps = client.fetch()
        preflight = DispatchPreflight.from_capabilities(caps)
        result = preflight.check("context.compile")
        assert result.status == PreflightStatus.PASS

    Full preflight with params::

        result = preflight.check(
            "lineage.get.v0_1",
            params={"target": "my-artifact"},
        )
        assert result.should_proceed
    """

    def __init__(
        self,
        *,
        validator: Optional[RunTypeValidator] = None,
        schema_helper: Optional[SchemaHelper] = None,
    ) -> None:
        self._validator = validator or RunTypeValidator()
        self._schema = schema_helper or SchemaHelper()

    @classmethod
    def from_capabilities(cls, capabilities_result: object) -> "DispatchPreflight":
        """Build a preflight checker from live capabilities.

        Constructs both the validator and schema helper from the
        same capabilities result to ensure consistency.
        """
        return cls(
            validator=RunTypeValidator.from_capabilities(capabilities_result),
            schema_helper=SchemaHelper.from_capabilities(capabilities_result),
        )

    def check(
        self,
        run_type: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> PreflightResult:
        """Run preflight checks on the intended dispatch.

        Steps:
          1. Validate the run type against known canonical names.
          2. Check request parameters against known schema.
          3. Return pass / warn / reject with guidance.
        """
        # Step 1: Validate run type
        type_result = self._validator.check(run_type)

        if type_result.status == RunTypeStatus.INVALID:
            suggestion = ""
            if type_result.suggestions:
                suggestion = (
                    f"Use the exact canonical name: "
                    f"{', '.join(type_result.suggestions)}"
                )
            else:
                suggestion = (
                    "Re-check capabilities via GET /mcp/v1/capabilities."
                )
            return PreflightResult(
                status=PreflightStatus.REJECT,
                run_type=run_type,
                reason=type_result.reason,
                suggested_next_step=suggestion,
            )

        if type_result.status == RunTypeStatus.UNKNOWN:
            return PreflightResult(
                status=PreflightStatus.REJECT,
                run_type=run_type,
                reason=type_result.reason,
                suggested_next_step=(
                    "Re-check capabilities via GET /mcp/v1/capabilities. "
                    "Do not guess run-type names."
                ),
            )

        # Step 2: Validate params against schema
        warnings: List[str] = []
        param_warnings = self._schema.validate_params(run_type, params)
        warnings.extend(param_warnings)

        # Step 3: Determine overall status
        if warnings:
            # Check if any warnings are about missing required params
            has_missing_required = any(
                "Required parameter" in w and "is missing" in w
                for w in warnings
            )
            if has_missing_required:
                return PreflightResult(
                    status=PreflightStatus.REJECT,
                    run_type=run_type,
                    reason="Required parameters are missing.",
                    suggested_next_step=(
                        "Consult schema for required parameters. "
                        f"Hint: {self._schema.get_hint(run_type).notes}"
                    ),
                    warnings=warnings,
                )
            return PreflightResult(
                status=PreflightStatus.WARN,
                run_type=run_type,
                reason="Preflight passed with warnings.",
                suggested_next_step="Review warnings before dispatch.",
                warnings=warnings,
            )

        return PreflightResult(
            status=PreflightStatus.PASS,
            run_type=run_type,
            reason="Run type is canonical and parameters are valid.",
        )

    def get_recovery_guidance(
        self, run_type: str, error_class: str = ""
    ) -> ErrorRecoveryGuidance:
        """Generate recovery guidance for a failed dispatch.

        Provides structured recovery actions based on the error class
        and validation state.
        """
        type_result = self._validator.check(run_type)
        actions: List[RecoveryAction] = []
        message = ""

        if type_result.status == RunTypeStatus.INVALID:
            message = (
                f"'{run_type}' is not a canonical run type. "
                "Exact canonical names are required."
            )
            if type_result.suggestions:
                actions.append(RecoveryAction(
                    action="Use exact canonical name",
                    detail=f"Try: {', '.join(type_result.suggestions)}",
                ))
            actions.append(RecoveryAction(
                action="Re-check capabilities",
                detail="GET /mcp/v1/capabilities for published guidance.",
            ))
            actions.append(RecoveryAction(
                action="Stop guessing",
                detail=(
                    "Run types are exact keys, not REST resource guesses. "
                    "Do not pluralize, singularize, or improvise."
                ),
            ))

        elif type_result.status == RunTypeStatus.UNKNOWN:
            message = (
                f"'{run_type}' is not recognized. "
                "The developer kit has no guidance for this name."
            )
            actions.append(RecoveryAction(
                action="Re-check capabilities",
                detail="GET /mcp/v1/capabilities for current guidance.",
            ))
            actions.append(RecoveryAction(
                action="Retrieve schema",
                detail="Consult schema discovery for valid run types.",
            ))
            actions.append(RecoveryAction(
                action="Do not dispatch blindly",
                detail=(
                    "Server rejection should not be the primary teacher. "
                    "Discover first, then dispatch."
                ),
            ))

        elif type_result.status == RunTypeStatus.VALID:
            message = (
                f"'{run_type}' is a valid canonical run type. "
                "Check request parameters or connectivity."
            )
            schema_hint = self._schema.get_hint(run_type)
            if schema_hint.available and schema_hint.required_params:
                actions.append(RecoveryAction(
                    action="Check required parameters",
                    detail=(
                        f"Required: {', '.join(schema_hint.required_params)}"
                    ),
                ))
            actions.append(RecoveryAction(
                action="Verify connectivity",
                detail="Ensure the boundary is reachable and token is valid.",
            ))

        if not error_class:
            error_class = _infer_error_class(type_result.status, run_type)

        return ErrorRecoveryGuidance(
            error_class=error_class,
            run_type=run_type,
            message=message,
            actions=actions,
        )


def _infer_error_class(status: RunTypeStatus, run_type: str) -> str:
    """Infer error class from validation status and run type name."""
    if status == RunTypeStatus.INVALID:
        # Check if it looks like a pluralization
        for suffix in ("s", "es", "ies"):
            if run_type.endswith(suffix):
                return "guessed_pluralization"
        return "invalid_run_type"
    if status == RunTypeStatus.UNKNOWN:
        return "unknown_run_type"
    return "dispatch_error"
