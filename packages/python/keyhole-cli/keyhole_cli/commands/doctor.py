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
    mode: str = "auto",
    runtime_url: str = "",
    verify: bool = False,
    previous_diagnostic_ref: str = "",
    repair_plan_ref: str = "",
    goal: str = "",
    mcp_url: str = "",
) -> CommandResult:
    """Execute environment diagnosis and return structured result.

    When *verify* is True, runs verification-after-repair mode.
    """
    op_mode = OperatingMode(mode)

    facts = collect_environment_facts(
        runtime_url=runtime_url,
        skip_runtime_check=(not runtime_url),
        mcp_url=mcp_url,
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
    effective_mode = result.get("mode", mode)
    verdict = result.get("verdict", "UNKNOWN")
    reason_codes = result.get("reason_codes", [])

    auto_promoted = "DOCTOR_AUTO_PROMOTED_TO_GOVERNED" in reason_codes
    boundary_live = "DOCTOR_MCP_BOUNDARY_REACHABLE" in reason_codes

    if ok:
        summary = f"Environment doctor: {verdict} ({effective_mode} mode)"
        if auto_promoted:
            summary += " [auto-promoted from auto]"
    else:
        root_groups = result.get("root_failure_groups", [])
        n_root = len(root_groups)
        summary = (
            f"Environment doctor: {verdict} ({effective_mode} mode) — "
            f"{n_root} root failure(s) identified"
        )

    # Next steps from repair plan + provisioning
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

    # Auto-suggest provisioning when MCP boundary is live
    if boundary_live:
        boundary_url = facts.mcp_boundary_url
        if not any("whoami" in s for s in next_steps):
            next_steps.append(
                f"MCP boundary live at {boundary_url}. "
                "Verify identity: keyhole whoami"
            )
        if not any("host" in s.lower() for s in next_steps):
            next_steps.append(
                "Check host configuration: keyhole host list"
            )
        if facts.mcp_operations:
            next_steps.append(
                f"Available operations: {', '.join(facts.mcp_operations[:5])}"
            )

    return CommandResult(
        command="doctor",
        success=ok,
        exit_code=EXIT_SUCCESS if ok else EXIT_FAILURE,
        data=result,
        next_steps=next_steps,
        summary=summary,
    )
