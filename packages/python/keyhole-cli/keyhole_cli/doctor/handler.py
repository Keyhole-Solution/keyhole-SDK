"""`keyhole doctor` — CE-V5-S41-08 orchestration handler.

Single entry point for doctor evaluation, repair plan computation,
verification-after-repair, repair JSON generation, and attestation.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .attestation import build_doctor_attestation
from .contract import (
    DoctorVerdict,
    EnvironmentFacts,
    OperatingMode,
    ReasonCode,
    RepairJson,
    RepairPlan,
)
from .diagnostics import run_diagnostics
from .repair_plan import compute_repair_plan
from .root_cause import annotate_diagnostic_with_roots
from .verify import verify_after_repair


def run_doctor_evaluation(
    facts: EnvironmentFacts,
    *,
    mode: OperatingMode = OperatingMode.LOCAL_ONLY,
    goal: str = "",
    include_repair: bool = True,
    include_attestation: bool = True,
) -> Dict[str, Any]:
    """Execute a full doctor evaluation.

    Pipeline:
      1. Run structured diagnostics
      2. Compute root-failure groups
      3. Compute minimal repair plan (if failures exist)
      4. Build repair JSON
      5. Build attestation

    Returns a dict with all artifacts.
    """
    # 1. Diagnostics
    diagnostic = run_diagnostics(facts, mode)

    # 2. Root-failure analysis
    diagnostic = annotate_diagnostic_with_roots(diagnostic)

    # 3. Repair plan (only if failures)
    repair_plan: Optional[RepairPlan] = None
    repair_json: Optional[Dict[str, Any]] = None

    if (
        include_repair
        and diagnostic.final_posture == DoctorVerdict.REJECT.value
    ):
        repair_plan = compute_repair_plan(diagnostic, goal=goal)

        # Build machine-readable repair JSON
        authority_notes = []
        for step in repair_plan.steps:
            if step.authority == "admin":
                authority_notes.append(
                    f"Step {step.step_id} requires admin/root privileges."
                )

        rj = RepairJson(
            diagnostic_result_ref=diagnostic.diagnostic_run_id,
            repair_plan_ref=repair_plan.plan_id,
            environment_facts_summary={
                "platform": facts.platform,
                "python_version": facts.python_version,
                "docker_available": facts.docker_available,
                "cli_installed": facts.cli_installed,
                "runtime_running": facts.runtime_running,
                "mcp_config_present": facts.mcp_config_present,
            },
            root_failures=[
                g.to_dict() for g in diagnostic.root_failure_groups
            ],
            steps=[s.to_dict() for s in repair_plan.steps],
            verification_steps=repair_plan.verification_steps,
            reason_codes=diagnostic.reason_codes,
            mode=mode.value,
            authority_notes=authority_notes,
        )
        repair_json = rj.to_dict()

        if ReasonCode.REPAIR_PLAN_REQUIRED.value not in diagnostic.reason_codes:
            diagnostic.reason_codes.append(
                ReasonCode.REPAIR_PLAN_REQUIRED.value
            )
            diagnostic.reason_codes = sorted(set(diagnostic.reason_codes))

    # 4. Attestation
    attestation = None
    if include_attestation:
        attestation = build_doctor_attestation(
            diagnostic=diagnostic,
            repair_plan=repair_plan,
        )

    return {
        "ok": diagnostic.final_posture == DoctorVerdict.ACCEPT.value,
        "verdict": diagnostic.final_posture,
        "mode": diagnostic.requested_mode or mode.value,
        "diagnostic": diagnostic.to_dict(),
        "root_failure_groups": [
            g.to_dict() for g in diagnostic.root_failure_groups
        ],
        "repair_plan": repair_plan.to_dict() if repair_plan else None,
        "repair_json": repair_json,
        "attestation": attestation.to_dict() if attestation else None,
        "reason_codes": diagnostic.reason_codes,
    }


def run_doctor_verify(
    facts: EnvironmentFacts,
    *,
    mode: OperatingMode = OperatingMode.LOCAL_ONLY,
    previous_diagnostic_ref: str = "",
    repair_plan_ref: str = "",
) -> Dict[str, Any]:
    """Run verification-after-repair.

    Re-evaluates the environment and reports whether the repair succeeded.
    """
    verification = verify_after_repair(
        facts,
        mode,
        previous_diagnostic_ref=previous_diagnostic_ref,
        repair_plan_ref=repair_plan_ref,
    )

    # Run full diagnostics for attestation
    diagnostic = run_diagnostics(facts, mode)
    diagnostic = annotate_diagnostic_with_roots(diagnostic)

    attestation = build_doctor_attestation(
        diagnostic=diagnostic,
        verification=verification,
    )

    return {
        "ok": verification.verified,
        "verdict": (
            DoctorVerdict.ACCEPT.value
            if verification.verified
            else DoctorVerdict.REJECT.value
        ),
        "mode": mode.value,
        "verification": verification.to_dict(),
        "diagnostic": diagnostic.to_dict(),
        "attestation": attestation.to_dict(),
        "reason_codes": attestation.reason_codes,
    }
