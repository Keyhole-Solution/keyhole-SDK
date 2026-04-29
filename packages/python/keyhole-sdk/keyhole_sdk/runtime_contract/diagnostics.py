"""Local runtime diagnostics — SDK-CLIENT-24 §10.4 §12.

Inspects the local environment for:
  - container runtime availability (Docker / Podman / Colima)
  - whether we are running inside a container
  - presence (and noncanonical status) of a local ``.venv``
  - basic OS/Python identity for runtime context claims

These diagnostics are advisory only. The MCP boundary remains the sole
authority for runtime trust classification.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

from keyhole_sdk.runtime_contract.models import RuntimeDiagnostics


def _detect_container_runtime() -> tuple[bool, str]:
    """Return (detected, kind). Empty kind when nothing detected."""
    candidates = ("docker", "podman", "colima", "nerdctl")
    for name in candidates:
        if shutil.which(name):
            return True, name
    return False, ""


def _detect_inside_container() -> bool:
    """Heuristic check whether this process is running inside a container."""
    # Standard container marker file
    if Path("/.dockerenv").exists():
        return True
    # cgroup hint
    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            content = cgroup.read_text(errors="ignore")
            if "docker" in content or "containerd" in content or "kubepods" in content:
                return True
    except OSError:
        pass
    # Standard env var honored by some runtimes
    if os.environ.get("KEYHOLE_IN_CONTAINER", "").lower() in ("1", "true", "yes"):
        return True
    return False


def _detect_local_venv(repo_root: Path) -> tuple[bool, str]:
    """Locate a local ``.venv`` directory, if any."""
    candidate = repo_root / ".venv"
    if candidate.exists():
        return True, str(candidate)
    return False, ""


def collect_diagnostics(
    *,
    repo_root: Optional[Path] = None,
    sdk_version: str = "",
    cli_version: str = "",
) -> RuntimeDiagnostics:
    """Collect local runtime diagnostics.

    The returned :class:`RuntimeDiagnostics` is advisory metadata. ``.venv``
    is always reported as ``local_venv_canonical=False`` — never elevate it
    to canonical proof truth (§12.3).
    """
    root = repo_root or Path.cwd()
    detected, kind = _detect_container_runtime()
    venv_present, venv_path = _detect_local_venv(root)
    return RuntimeDiagnostics(
        container_runtime_detected=detected,
        container_runtime_kind=kind,
        inside_container=_detect_inside_container(),
        local_venv_present=venv_present,
        local_venv_path=venv_path,
        local_venv_canonical=False,  # invariant §12.3
        platform=f"{platform.system().lower()}/{platform.machine().lower()}",
        python_version=sys.version.split()[0] if sys.version else "",
        sdk_version=sdk_version,
        cli_version=cli_version,
    )
