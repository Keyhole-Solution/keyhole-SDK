"""`keyhole doctor` — CE-V5-S41-08 structured diagnostic evaluation.

Evaluates environment facts against the required posture for the
requested operating mode.  Emits structured CheckResult objects —
never prose-only output.
"""
from __future__ import annotations

from typing import List

from .contract import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    DiagnosticResult,
    DoctorVerdict,
    EnvironmentFacts,
    MAX_PYTHON_VERSION,
    MIN_PYTHON_VERSION,
    OperatingMode,
    ReasonCode,
    SUPPORTED_PLATFORMS,
)


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_platform(facts: EnvironmentFacts) -> CheckResult:
    if facts.platform in SUPPORTED_PLATFORMS:
        return CheckResult(
            check_name="platform_supported",
            category=CheckCategory.PLATFORM.value,
            status=CheckStatus.PASS.value,
            message=f"Platform '{facts.platform}' is supported.",
        )
    return CheckResult(
        check_name="platform_supported",
        category=CheckCategory.PLATFORM.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_UNSUPPORTED_ENVIRONMENT.value,
        message=(
            f"Platform '{facts.platform}' is not in the supported set: "
            f"{sorted(SUPPORTED_PLATFORMS)}."
        ),
        is_root=True,
    )


def check_python_available(facts: EnvironmentFacts) -> CheckResult:
    if facts.python_available:
        return CheckResult(
            check_name="python_available",
            category=CheckCategory.PYTHON.value,
            status=CheckStatus.PASS.value,
            message=f"Python {facts.python_version} is available.",
        )
    return CheckResult(
        check_name="python_available",
        category=CheckCategory.PYTHON.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_PYTHON_MISSING.value,
        message="Python is not available.",
        is_root=True,
    )


def check_python_version(facts: EnvironmentFacts) -> CheckResult:
    if not facts.python_available:
        return CheckResult(
            check_name="python_version",
            category=CheckCategory.PYTHON.value,
            status=CheckStatus.FAIL.value,
            reason_code=ReasonCode.DOCTOR_PYTHON_VERSION_UNSUPPORTED.value,
            message="Python is not available; cannot check version.",
            downstream_of="python_available",
        )
    ver = facts.python_version_tuple
    if len(ver) >= 2 and MIN_PYTHON_VERSION <= ver[:2] <= MAX_PYTHON_VERSION:
        return CheckResult(
            check_name="python_version",
            category=CheckCategory.PYTHON.value,
            status=CheckStatus.PASS.value,
            message=(
                f"Python {facts.python_version} is within supported range "
                f"{'.'.join(map(str, MIN_PYTHON_VERSION))}"
                f"–{'.'.join(map(str, MAX_PYTHON_VERSION))}."
            ),
        )
    return CheckResult(
        check_name="python_version",
        category=CheckCategory.PYTHON.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_PYTHON_VERSION_UNSUPPORTED.value,
        message=(
            f"Python {facts.python_version} is outside supported range "
            f"{'.'.join(map(str, MIN_PYTHON_VERSION))}"
            f"–{'.'.join(map(str, MAX_PYTHON_VERSION))}."
        ),
        is_root=True,
    )


def check_cli_installed(facts: EnvironmentFacts) -> CheckResult:
    if facts.cli_installed:
        return CheckResult(
            check_name="cli_installed",
            category=CheckCategory.CLI.value,
            status=CheckStatus.PASS.value,
            message=f"Keyhole CLI {facts.cli_version} is installed.",
        )
    return CheckResult(
        check_name="cli_installed",
        category=CheckCategory.CLI.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_CLI_NOT_INSTALLED.value,
        message="Keyhole CLI is not installed.",
        is_root=True,
    )


def check_docker_available(facts: EnvironmentFacts) -> CheckResult:
    if facts.docker_available:
        return CheckResult(
            check_name="docker_available",
            category=CheckCategory.DOCKER.value,
            status=CheckStatus.PASS.value,
            message=f"Docker is available: {facts.docker_version}.",
        )
    return CheckResult(
        check_name="docker_available",
        category=CheckCategory.DOCKER.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_DOCKER_UNAVAILABLE.value,
        message="Docker is not available.",
        is_root=True,
    )


def check_compose_available(facts: EnvironmentFacts) -> CheckResult:
    if not facts.docker_available:
        return CheckResult(
            check_name="compose_available",
            category=CheckCategory.DOCKER.value,
            status=CheckStatus.FAIL.value,
            reason_code=ReasonCode.DOCTOR_COMPOSE_UNAVAILABLE.value,
            message="Docker Compose unavailable because Docker is not available.",
            downstream_of="docker_available",
        )
    if facts.compose_available:
        return CheckResult(
            check_name="compose_available",
            category=CheckCategory.DOCKER.value,
            status=CheckStatus.PASS.value,
            message=f"Docker Compose is available: {facts.compose_version}.",
        )
    return CheckResult(
        check_name="compose_available",
        category=CheckCategory.DOCKER.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_COMPOSE_UNAVAILABLE.value,
        message="Docker Compose is not available.",
        is_root=True,
    )


def check_runtime_running(
    facts: EnvironmentFacts, mode: OperatingMode
) -> CheckResult:
    # When MCP boundary is reachable, local runtime is not required
    if facts.mcp_boundary_reachable:
        return CheckResult(
            check_name="runtime_running",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.SKIP.value,
            message="Local runtime check skipped (MCP boundary is reachable).",
        )
    if not facts.docker_available and mode == OperatingMode.LOCAL_ONLY:
        return CheckResult(
            check_name="runtime_running",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.FAIL.value,
            reason_code=ReasonCode.DOCTOR_RUNTIME_NOT_RUNNING.value,
            message="Runtime not running; Docker unavailable.",
            downstream_of="docker_available",
        )
    if facts.runtime_running:
        return CheckResult(
            check_name="runtime_running",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.PASS.value,
            message="Keyhole runtime is running.",
        )
    if mode == OperatingMode.LOCAL_ONLY and not facts.runtime_url:
        return CheckResult(
            check_name="runtime_running",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.SKIP.value,
            message="Runtime check skipped (no URL, local-only mode).",
        )
    return CheckResult(
        check_name="runtime_running",
        category=CheckCategory.RUNTIME.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_RUNTIME_NOT_RUNNING.value,
        message="Keyhole runtime is not running.",
        is_root=True,
    )


def check_runtime_reachable(
    facts: EnvironmentFacts, mode: OperatingMode
) -> CheckResult:
    # When MCP boundary is reachable, local runtime reachability is not required
    if facts.mcp_boundary_reachable:
        return CheckResult(
            check_name="runtime_reachable",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.SKIP.value,
            message="Local runtime reachability skipped (MCP boundary is reachable).",
        )
    if not facts.runtime_running:
        if mode == OperatingMode.LOCAL_ONLY and not facts.runtime_url:
            return CheckResult(
                check_name="runtime_reachable",
                category=CheckCategory.RUNTIME.value,
                status=CheckStatus.SKIP.value,
                message="Runtime reachability skipped (not running, local-only).",
            )
        return CheckResult(
            check_name="runtime_reachable",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.FAIL.value,
            reason_code=ReasonCode.DOCTOR_RUNTIME_UNREACHABLE.value,
            message="Runtime unreachable because it is not running.",
            downstream_of="runtime_running",
        )
    if facts.runtime_reachable:
        return CheckResult(
            check_name="runtime_reachable",
            category=CheckCategory.RUNTIME.value,
            status=CheckStatus.PASS.value,
            message="Keyhole runtime is reachable.",
        )
    return CheckResult(
        check_name="runtime_reachable",
        category=CheckCategory.RUNTIME.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_RUNTIME_UNREACHABLE.value,
        message="Keyhole runtime is not reachable.",
        is_root=True,
    )


def check_mcp_config(
    facts: EnvironmentFacts, mode: OperatingMode
) -> CheckResult:
    if mode in (OperatingMode.LOCAL_ONLY,):
        return CheckResult(
            check_name="mcp_config",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.SKIP.value,
            message="MCP configuration not required for local-only mode.",
        )
    if facts.mcp_config_present:
        return CheckResult(
            check_name="mcp_config",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.PASS.value,
            message=f"MCP configuration found at {facts.mcp_config_path}.",
        )
    # In auto/governed modes, config file is informational — boundary
    # reachability is the real signal.
    if facts.mcp_boundary_reachable:
        return CheckResult(
            check_name="mcp_config",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.PASS.value,
            message=(
                "No local MCP config file found, but MCP boundary is "
                f"reachable at {facts.mcp_boundary_url}."
            ),
        )
    return CheckResult(
        check_name="mcp_config",
        category=CheckCategory.MCP_CONFIG.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_MCP_CONFIG_MISSING.value,
        message="MCP configuration not found. Required for governed mode.",
        is_root=True,
    )


def check_mcp_boundary(
    facts: EnvironmentFacts, mode: OperatingMode
) -> CheckResult:
    """Check whether the MCP boundary capabilities endpoint is reachable."""
    if mode == OperatingMode.LOCAL_ONLY:
        return CheckResult(
            check_name="mcp_boundary",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.SKIP.value,
            message="MCP boundary check skipped (local-only mode).",
        )
    if facts.mcp_boundary_reachable:
        msg = f"MCP boundary reachable at {facts.mcp_boundary_url}"
        if facts.mcp_contract_version:
            msg += f" (contract {facts.mcp_contract_version})"
        return CheckResult(
            check_name="mcp_boundary",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.PASS.value,
            reason_code=ReasonCode.DOCTOR_MCP_BOUNDARY_REACHABLE.value,
            message=msg + ".",
        )
    # Boundary unreachable is informational when config file exists
    if facts.mcp_config_present:
        return CheckResult(
            check_name="mcp_boundary",
            category=CheckCategory.MCP_CONFIG.value,
            status=CheckStatus.SKIP.value,
            reason_code=ReasonCode.DOCTOR_MCP_BOUNDARY_UNREACHABLE.value,
            message=(
                "MCP boundary is not reachable, but config file exists at "
                f"{facts.mcp_config_path}."
            ),
        )
    return CheckResult(
        check_name="mcp_boundary",
        category=CheckCategory.MCP_CONFIG.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_MCP_BOUNDARY_UNREACHABLE.value,
        message="MCP boundary is not reachable.",
        is_root=True,
    )


def check_sdk_runtime_compatibility(facts: EnvironmentFacts) -> CheckResult:
    if not facts.sdk_installed:
        return CheckResult(
            check_name="sdk_runtime_compatibility",
            category=CheckCategory.SDK.value,
            status=CheckStatus.SKIP.value,
            message="SDK not installed; compatibility check skipped.",
        )
    if not facts.runtime_version:
        return CheckResult(
            check_name="sdk_runtime_compatibility",
            category=CheckCategory.SDK.value,
            status=CheckStatus.SKIP.value,
            message="Runtime version unknown; compatibility check skipped.",
        )
    sdk_parts = facts.sdk_version.split(".")[:2]
    rt_parts = facts.runtime_version.split(".")[:2]
    if sdk_parts == rt_parts:
        return CheckResult(
            check_name="sdk_runtime_compatibility",
            category=CheckCategory.SDK.value,
            status=CheckStatus.PASS.value,
            message=(
                f"SDK {facts.sdk_version} compatible with "
                f"runtime {facts.runtime_version}."
            ),
        )
    return CheckResult(
        check_name="sdk_runtime_compatibility",
        category=CheckCategory.SDK.value,
        status=CheckStatus.FAIL.value,
        reason_code=ReasonCode.DOCTOR_SDK_RUNTIME_VERSION_MISMATCH.value,
        message=(
            f"SDK {facts.sdk_version} may be incompatible with "
            f"runtime {facts.runtime_version}."
        ),
        is_root=True,
    )


# ---------------------------------------------------------------------------
# Full diagnostic evaluation
# ---------------------------------------------------------------------------


def run_diagnostics(
    facts: EnvironmentFacts,
    mode: OperatingMode = OperatingMode.LOCAL_ONLY,
) -> DiagnosticResult:
    """Run all diagnostic checks.  Deterministic: same inputs → same output."""

    # ── Auto mode: promote to governed when MCP boundary is reachable ──
    effective_mode = mode
    auto_promoted = False
    if mode == OperatingMode.AUTO:
        if facts.mcp_boundary_reachable or facts.mcp_config_present:
            effective_mode = OperatingMode.GOVERNED
            auto_promoted = True
        else:
            effective_mode = OperatingMode.LOCAL_ONLY

    checks: List[CheckResult] = [
        check_platform(facts),
        check_python_available(facts),
        check_python_version(facts),
        check_cli_installed(facts),
        check_docker_available(facts),
        check_compose_available(facts),
        check_runtime_running(facts, effective_mode),
        check_runtime_reachable(facts, effective_mode),
        check_mcp_config(facts, effective_mode),
        check_mcp_boundary(facts, effective_mode),
        check_sdk_runtime_compatibility(facts),
    ]

    reason_codes: List[str] = []
    if auto_promoted:
        reason_codes.append(
            ReasonCode.DOCTOR_AUTO_PROMOTED_TO_GOVERNED.value
        )
    for c in checks:
        if c.reason_code:
            reason_codes.append(c.reason_code)

    failed = [c for c in checks if c.status == CheckStatus.FAIL.value]

    if not failed:
        if effective_mode == OperatingMode.LOCAL_ONLY:
            reason_codes.append(ReasonCode.DOCTOR_LOCAL_MODE_READY.value)
        else:
            reason_codes.append(ReasonCode.DOCTOR_GOVERNED_MODE_READY.value)
        posture = DoctorVerdict.ACCEPT.value
    else:
        if effective_mode == OperatingMode.GOVERNED:
            reason_codes.append(
                ReasonCode.DOCTOR_GOVERNED_MODE_INCOMPLETE.value
            )
        posture = DoctorVerdict.REJECT.value

    reason_codes.append(ReasonCode.NO_HIDDEN_MUTATION_ENFORCED.value)

    return DiagnosticResult(
        environment_summary=facts.to_dict(),
        check_results=checks,
        reason_codes=sorted(set(reason_codes)),
        requested_mode=effective_mode.value,
        final_posture=posture,
    )
