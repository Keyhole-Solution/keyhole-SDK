"""`keyhole doctor` — environment diagnosis and supported-profile validation."""

from __future__ import annotations

from keyhole_cli.profile import detect_profile
from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_UNSUPPORTED


def run_doctor() -> CommandResult:
    """Execute environment diagnosis and return structured result."""
    profile = detect_profile()

    exit_code = EXIT_SUCCESS if (profile.supported and not profile.failed_checks) else EXIT_UNSUPPORTED

    return CommandResult(
        command="doctor",
        success=profile.supported and not profile.failed_checks,
        exit_code=exit_code,
        data={
            "supported": profile.supported,
            "detected_profile": profile.detected_profile,
            "os_family": profile.os_family,
            "shell": profile.shell,
            "is_wsl": profile.is_wsl,
            "docker_available": profile.docker_available,
            "compose_available": profile.compose_available,
            "required_checks": profile.required_checks,
            "failed_checks": profile.failed_checks,
        },
        warnings=profile.warnings,
        next_steps=profile.next_steps,
        summary=(
            f"Environment supported: profile={profile.detected_profile}"
            if profile.supported and not profile.failed_checks
            else f"Environment issues detected: profile={profile.detected_profile}, "
            f"failed={profile.failed_checks}"
        ),
    )
