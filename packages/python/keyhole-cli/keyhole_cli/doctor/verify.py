"""`keyhole doctor` — CE-V5-S41-08 verification-after-repair.

Re-runs diagnostics after the user or agent applies the recommended
repair and compares the result to the previous diagnostic.
"""
from __future__ import annotations

from .contract import (
    CheckStatus,
    DiagnosticResult,
    DoctorVerdict,
    EnvironmentFacts,
    OperatingMode,
    ReasonCode,
    VerificationResult,
)
from .diagnostics import run_diagnostics
from .root_cause import annotate_diagnostic_with_roots


def verify_after_repair(
    facts: EnvironmentFacts,
    mode: OperatingMode,
    *,
    previous_diagnostic_ref: str = "",
    repair_plan_ref: str = "",
) -> VerificationResult:
    """Run diagnostics again and compare to previous state.

    Returns a VerificationResult indicating whether the environment
    is now healthy or which failures remain.
    """
    diag = run_diagnostics(facts, mode)
    diag = annotate_diagnostic_with_roots(diag)

    passed = sum(
        1 for c in diag.check_results
        if c.status == CheckStatus.PASS.value
    )
    failed = sum(
        1 for c in diag.check_results
        if c.status == CheckStatus.FAIL.value
    )
    total = len(diag.check_results)

    remaining = [
        c.check_name
        for c in diag.check_results
        if c.status == CheckStatus.FAIL.value
    ]

    verified = diag.final_posture == DoctorVerdict.ACCEPT.value

    return VerificationResult(
        previous_diagnostic_ref=previous_diagnostic_ref,
        repair_plan_ref=repair_plan_ref,
        checks_passed=passed,
        checks_failed=failed,
        checks_total=total,
        remaining_failures=remaining,
        verified=verified,
    )
