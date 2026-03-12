"""`keyhole doctor` — environment diagnosis and minimal repair guidance.

CE-V5-S41-08: Full structured diagnostics, root-failure classification,
minimal repair plan, machine-readable repair JSON, and
verification-after-repair flow.

Backward compatible: run_doctor() still returns CommandResult.
"""

from __future__ import annotations

from keyhole_cli.doctor.contract import OperatingMode
from keyhole_cli.doctor.facts import collect_environment_facts
from keyhole_cli.doctor.handler import run_doctor_evaluation, run_doctor_verify
from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE


def run_doctor(
    *,
    mode: str = "local_only",
    runtime_url: str = "",
    verify: bool = False,
    previous_diagnostic_ref: str = "",
    repair_plan_ref: str = "",
    goal: str = "",
) -> CommandResult:
    """Execute environment diagnosis and return structured result.

    When *verify* is True, runs verification-after-repair mode.
    """
    op_mode = OperatingMode(mode)

    facts = collect_environment_facts(
        runtime_url=runtime_url,
        skip_runtime_check=(not runtime_url),
    )

    if verify:
        result = run_doctor_verify(
            facts,
            mode=op_mode,
            previous_diagnostic_ref=previous_diagnostic_ref,
            repair_plan_ref=repair_plan_ref,
        )
    else:
        result = run_doctor_evaluation(
            facts,
            mode=op_mode,
            goal=goal,
        )

    ok = result.get("ok", False)

    # Build human-readable summary
    verdict = result.get("verdict", "UNKNOWN")
    if ok:
        summary = f"Environment doctor: {verdict} ({mode} mode)"
    else:
        root_groups = result.get("root_failure_groups", [])
        n_root = len(root_groups)
        summary = (
            f"Environment doctor: {verdict} ({mode} mode) — "
            f"{n_root} root failure(s) identified"
        )

    # Next steps from repair plan
    next_steps = []
    repair_plan = result.get("repair_plan")
    if repair_plan and repair_plan.get("steps"):
        for step in repair_plan["steps"]:
            desc = step.get("description", "")
            cmd = step.get("command", "")
            if cmd and not cmd.startswith("http"):
                next_steps.append(f"{desc}: {cmd}")
            else:
                next_steps.append(desc)

    return CommandResult(
        command="doctor",
        success=ok,
        exit_code=EXIT_SUCCESS if ok else EXIT_FAILURE,
        data=result,
        next_steps=next_steps,
        summary=summary,
    )
