"""`keyhole doctor` — CE-V5-S41-08 minimal repair plan computation.

Computes the smallest lawful repair set (RestorationSet) from
root-failure analysis.  Steps are ordered so earlier steps resolve
conditions needed by later steps.  Role-safe: guidance only.
"""
from __future__ import annotations

from typing import Dict, List

from .contract import (
    CheckStatus,
    DiagnosticResult,
    OperatingMode,
    ReasonCode,
    RepairAuthority,
    RepairPlan,
    RepairStep,
    RepairStepKind,
    RootFailureGroup,
)

# ---------------------------------------------------------------------------
# Repair rule registry: reason_code → step template
# ---------------------------------------------------------------------------

_REPAIR_RULES: Dict[str, Dict] = {
    ReasonCode.DOCTOR_UNSUPPORTED_ENVIRONMENT.value: {
        "kind": RepairStepKind.DOC_LINK.value,
        "description": (
            "This platform is not in the supported set. "
            "Use Linux, macOS, or Windows (WSL) for development."
        ),
        "doc_link": (
            "https://github.com/Keyhole-Solution/keyhole-developer-kit"
            "#supported-environments"
        ),
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'keyhole doctor' again on a supported OS.",
    },
    ReasonCode.DOCTOR_PYTHON_MISSING.value: {
        "kind": RepairStepKind.INSTALL.value,
        "description": "Install Python 3.9 or later.",
        "command": "https://www.python.org/downloads/",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'python3 --version'.",
    },
    ReasonCode.DOCTOR_PYTHON_VERSION_UNSUPPORTED.value: {
        "kind": RepairStepKind.INSTALL.value,
        "description": "Upgrade or install a supported Python version (3.9–3.13).",
        "command": "https://www.python.org/downloads/",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'python3 --version'.",
    },
    ReasonCode.DOCTOR_CLI_NOT_INSTALLED.value: {
        "kind": RepairStepKind.COMMAND.value,
        "description": "Install the Keyhole CLI.",
        "command": "pip install keyhole-cli",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'keyhole --version'.",
    },
    ReasonCode.DOCTOR_DOCKER_UNAVAILABLE.value: {
        "kind": RepairStepKind.INSTALL.value,
        "description": "Install Docker.",
        "command": "https://docs.docker.com/get-docker/",
        "doc_link": "https://docs.docker.com/get-docker/",
        "authority": RepairAuthority.ADMIN.value,
        "verification_hint": "Run 'docker --version'.",
    },
    ReasonCode.DOCTOR_COMPOSE_UNAVAILABLE.value: {
        "kind": RepairStepKind.INSTALL.value,
        "description": "Install Docker Compose.",
        "command": "https://docs.docker.com/compose/install/",
        "doc_link": "https://docs.docker.com/compose/install/",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'docker compose version'.",
    },
    ReasonCode.DOCTOR_RUNTIME_NOT_RUNNING.value: {
        "kind": RepairStepKind.COMMAND.value,
        "description": "Start the Keyhole local runtime.",
        "command": "keyhole runtime start",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'keyhole runtime status'.",
    },
    ReasonCode.DOCTOR_RUNTIME_UNREACHABLE.value: {
        "kind": RepairStepKind.COMMAND.value,
        "description": (
            "Verify runtime is accessible. Check logs and network."
        ),
        "command": "keyhole runtime status",
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'keyhole doctor --mode governed'.",
    },
    ReasonCode.DOCTOR_MCP_CONFIG_MISSING.value: {
        "kind": RepairStepKind.FILE_CREATE.value,
        "description": (
            "Create MCP configuration at ~/.keyhole/mcp.json with your "
            "runtime URL and credentials."
        ),
        "command": "keyhole init --governed",
        "doc_link": (
            "https://github.com/Keyhole-Solution/keyhole-developer-kit"
            "#governed-mode-setup"
        ),
        "authority": RepairAuthority.USER.value,
        "verification_hint": "Run 'keyhole doctor --mode governed'.",
    },
    ReasonCode.DOCTOR_SDK_RUNTIME_VERSION_MISMATCH.value: {
        "kind": RepairStepKind.COMMAND.value,
        "description": (
            "Update keyhole-sdk to match the runtime version."
        ),
        "command": "pip install --upgrade keyhole-sdk",
        "authority": RepairAuthority.USER.value,
        "verification_hint": (
            "Run 'python -c \"import keyhole_sdk; "
            "print(keyhole_sdk.__version__)\"'."
        ),
    },
}

# Order in which reason codes should be resolved
_REPAIR_ORDER = [
    ReasonCode.DOCTOR_UNSUPPORTED_ENVIRONMENT.value,
    ReasonCode.DOCTOR_PYTHON_MISSING.value,
    ReasonCode.DOCTOR_PYTHON_VERSION_UNSUPPORTED.value,
    ReasonCode.DOCTOR_CLI_NOT_INSTALLED.value,
    ReasonCode.DOCTOR_DOCKER_UNAVAILABLE.value,
    ReasonCode.DOCTOR_COMPOSE_UNAVAILABLE.value,
    ReasonCode.DOCTOR_RUNTIME_NOT_RUNNING.value,
    ReasonCode.DOCTOR_RUNTIME_UNREACHABLE.value,
    ReasonCode.DOCTOR_MCP_CONFIG_MISSING.value,
    ReasonCode.DOCTOR_SDK_RUNTIME_VERSION_MISMATCH.value,
]


def compute_repair_plan(
    diagnostic: DiagnosticResult,
    *,
    goal: str = "",
) -> RepairPlan:
    """Compute the minimal repair plan from root failures only.

    Steps target root causes — downstream symptoms are not repeated.
    Steps are ordered so prerequisites are resolved first.
    """
    # Collect root-failure reason codes
    root_codes: List[str] = []
    for g in diagnostic.root_failure_groups:
        if g.root_reason_code and g.root_reason_code not in root_codes:
            root_codes.append(g.root_reason_code)

    # If no root groups computed yet, fall back to all failed checks
    if not root_codes:
        for c in diagnostic.check_results:
            if (
                c.status == CheckStatus.FAIL.value
                and c.is_root
                and c.reason_code
                and c.reason_code not in root_codes
            ):
                root_codes.append(c.reason_code)

    # Order by _REPAIR_ORDER
    ordered_codes = [rc for rc in _REPAIR_ORDER if rc in root_codes]
    # Append any not in the canonical order
    for rc in root_codes:
        if rc not in ordered_codes:
            ordered_codes.append(rc)

    # Filter downstream: if a root explains a downstream,
    # don't also add the downstream's repair
    downstream_codes = set()
    for g in diagnostic.root_failure_groups:
        for dc_name in g.downstream_checks:
            for c in diagnostic.check_results:
                if c.check_name == dc_name and c.reason_code:
                    downstream_codes.add(c.reason_code)

    steps: List[RepairStep] = []
    authority_notes: List[str] = []
    verification_hints: List[str] = []

    for idx, rc in enumerate(ordered_codes):
        if rc in downstream_codes:
            continue
        rule = _REPAIR_RULES.get(rc)
        if not rule:
            continue
        step = RepairStep(
            step_id=f"step-{idx + 1}",
            order=idx + 1,
            kind=rule["kind"],
            description=rule["description"],
            command=rule.get("command", ""),
            authority=rule.get("authority", RepairAuthority.USER.value),
            required=True,
            addresses_check="",
            addresses_reason_code=rc,
            verification_hint=rule.get("verification_hint", ""),
            doc_link=rule.get("doc_link", ""),
        )
        steps.append(step)
        if step.authority == RepairAuthority.ADMIN.value:
            authority_notes.append(
                f"Step {step.step_id} requires admin/root privileges."
            )
        if step.verification_hint:
            verification_hints.append(step.verification_hint)

    # Always end with re-run doctor as final verification
    verification_hints.append(
        f"Run 'keyhole doctor --mode {diagnostic.requested_mode}' to verify."
    )

    return RepairPlan(
        requested_goal=goal or "restore environment health",
        requested_mode=diagnostic.requested_mode,
        root_failures_addressed=ordered_codes,
        steps=steps,
        verification_steps=verification_hints,
    )
