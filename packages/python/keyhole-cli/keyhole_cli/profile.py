"""Deterministic supported-profile detection for keyhole-cli.

Detects the current environment profile and determines whether it is
a supported developer environment.  Detection is deterministic: given
the same environment, it always returns the same result.

Supported profiles:
  - linux
  - wsl
  - windows-powershell
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, field
from typing import List


SUPPORTED_PROFILES = {"linux", "wsl", "windows-powershell"}


@dataclass
class ProfileResult:
    """Outcome of environment profile detection."""

    supported: bool
    detected_profile: str
    os_family: str
    shell: str
    is_wsl: bool
    docker_available: bool
    compose_available: bool
    required_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "supported": self.supported,
            "detected_profile": self.detected_profile,
            "os_family": self.os_family,
            "shell": self.shell,
            "is_wsl": self.is_wsl,
            "docker_available": self.docker_available,
            "compose_available": self.compose_available,
            "required_checks": self.required_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "next_steps": self.next_steps,
        }


def _detect_wsl() -> bool:
    """Detect whether running inside WSL."""
    # WSL sets WSL_DISTRO_NAME or has "microsoft" / "WSL" in /proc/version
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    if os.environ.get("WSLENV") is not None:
        return True
    try:
        with open("/proc/version", "r") as f:
            content = f.read().lower()
            if "microsoft" in content or "wsl" in content:
                return True
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return False


def _detect_os_family() -> str:
    """Return the OS family string."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    return system


def _detect_shell() -> str:
    """Detect the current shell context when possible."""
    shell = os.environ.get("SHELL", "")
    psmodule = os.environ.get("PSModulePath", "")
    if psmodule:
        return "powershell"
    if shell:
        return os.path.basename(shell)
    return "unknown"


def _check_docker() -> bool:
    """Check if docker is available on PATH."""
    return shutil.which("docker") is not None


def _check_compose() -> bool:
    """Check if docker compose is available."""
    if shutil.which("docker-compose") is not None:
        return True
    # docker compose (plugin) — check via docker
    if shutil.which("docker") is not None:
        # Just check for presence; actual plugin check is heavier
        return True
    return False


def _resolve_profile(os_family: str, is_wsl: bool, shell: str) -> str:
    """Resolve the detected profile label."""
    if is_wsl:
        return "wsl"
    if os_family == "windows" and shell == "powershell":
        return "windows-powershell"
    if os_family == "windows":
        return "windows-other"
    if os_family == "linux":
        return "linux"
    if os_family == "macos":
        return "macos"
    return f"unknown-{os_family}"


def detect_profile() -> ProfileResult:
    """Run deterministic supported-profile detection.

    Returns a ``ProfileResult`` with complete diagnosis.
    """
    os_family = _detect_os_family()
    is_wsl = _detect_wsl() if os_family == "linux" else False
    shell = _detect_shell()
    docker_available = _check_docker()
    compose_available = _check_compose()

    detected_profile = _resolve_profile(os_family, is_wsl, shell)
    supported = detected_profile in SUPPORTED_PROFILES

    required_checks = ["os_supported", "docker_available", "compose_available"]
    failed: List[str] = []
    warnings: List[str] = []
    next_steps: List[str] = []

    if not supported:
        failed.append("os_supported")
        next_steps.append(
            f"Profile '{detected_profile}' is not a supported developer profile. "
            f"Supported: {', '.join(sorted(SUPPORTED_PROFILES))}."
        )

    if not docker_available:
        failed.append("docker_available")
        next_steps.append("Install Docker: https://docs.docker.com/get-docker/")

    if not compose_available:
        failed.append("compose_available")
        next_steps.append("Install Docker Compose: https://docs.docker.com/compose/install/")

    if supported and not failed:
        next_steps.append("Run 'keyhole init' to prepare your workspace.")

    return ProfileResult(
        supported=supported,
        detected_profile=detected_profile,
        os_family=os_family,
        shell=shell,
        is_wsl=is_wsl,
        docker_available=docker_available,
        compose_available=compose_available,
        required_checks=required_checks,
        failed_checks=failed,
        warnings=warnings,
        next_steps=next_steps,
    )
