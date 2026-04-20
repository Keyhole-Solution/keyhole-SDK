"""`keyhole doctor` — CE-V5-S41-08 environment fact collection.

Collects deterministic environment facts from observable local state.
No mutation, no hidden assumptions — only reads.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Optional, Tuple

from .contract import EnvironmentFacts


def _run_cmd(cmd: list, timeout: int = 5) -> Optional[str]:
    """Run a command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _detect_wsl() -> bool:
    """Detect whether running inside WSL."""
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
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    return system


def _detect_shell() -> str:
    shell = os.environ.get("SHELL", "")
    psmodule = os.environ.get("PSModulePath", "")
    if psmodule:
        return "powershell"
    if shell:
        return os.path.basename(shell)
    return "unknown"


def _check_docker() -> Tuple[bool, str]:
    out = _run_cmd(["docker", "--version"])
    if out:
        return True, out
    return False, ""


def _check_compose() -> Tuple[bool, str]:
    out = _run_cmd(["docker", "compose", "version"])
    if out:
        return True, out
    out = _run_cmd(["docker-compose", "--version"])
    if out:
        return True, out
    return False, ""


def _check_cli() -> Tuple[bool, str]:
    # Prefer `keyhole --help` since --version is not always registered
    if shutil.which("keyhole"):
        out = _run_cmd(["keyhole", "--version"])
        if out:
            return True, out
        # --version may not exist; confirm via --help (exit 0 = installed)
        out = _run_cmd(["keyhole", "--help"])
        if out:
            try:
                import keyhole_cli  # type: ignore[import-untyped]
                ver = getattr(keyhole_cli, "__version__", "installed")
            except ImportError:
                ver = "installed"
            return True, ver
    # Fallback: importable check
    try:
        import keyhole_cli  # type: ignore[import-untyped]
        ver = getattr(keyhole_cli, "__version__", "installed")
        return True, ver
    except ImportError:
        pass
    return False, ""


def _check_sdk() -> Tuple[bool, str]:
    try:
        out = _run_cmd(
            [sys.executable, "-c",
             "import keyhole_sdk; print(keyhole_sdk.__version__)"]
        )
        if out:
            return True, out
    except Exception:
        pass
    return False, ""


def _check_pipx() -> bool:
    return shutil.which("pipx") is not None


def _check_mcp_config() -> Tuple[bool, str]:
    candidates = [
        # CLI-specific locations
        os.path.expanduser("~/.keyhole/mcp.json"),
        os.path.expanduser("~/.config/keyhole/mcp.json"),
        ".keyhole/mcp.json",
        # VS Code workspace-level
        ".vscode/mcp.json",
        "mcp.json",
        # VS Code user-level
        os.path.expanduser("~/.vscode-server/data/User/globalStorage/mcp.json"),
        os.path.expanduser("~/.config/Code/User/globalStorage/mcp.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return True, path
    return False, ""


def _check_mcp_boundary(url: str) -> Tuple[bool, str, list]:
    """Probe the MCP boundary capabilities endpoint (unauthenticated, read-only).

    Returns (reachable, contract_version, operations_list).
    """
    if not url:
        return False, "", []
    try:
        import urllib.request
        import json as _json

        caps_url = url.rstrip("/") + "/mcp/v1/capabilities"
        req = urllib.request.Request(caps_url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                body = _json.loads(resp.read().decode("utf-8"))
                version = body.get("contract_version", "")
                ops = body.get("operations", [])
                return True, version, ops
    except Exception:
        pass
    return False, "", []


def _check_runtime(url: str) -> Tuple[bool, bool, str]:
    """Check if runtime is running and reachable at the given URL."""
    try:
        import urllib.request

        health_url = url.rstrip("/") + "/livez"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return True, True, ""
    except Exception:
        pass
    return False, False, ""


def collect_environment_facts(
    *,
    runtime_url: str = "",
    skip_runtime_check: bool = False,
    mcp_url: str = "",
) -> EnvironmentFacts:
    """Collect all observable environment facts.

    Reads system state.  Never modifies it.
    """
    plat = sys.platform
    os_family = _detect_os_family()
    is_wsl = _detect_wsl() if os_family == "linux" else False
    shell = _detect_shell()

    py_version = platform.python_version()
    py_tuple = tuple(sys.version_info[:3])

    docker_avail, docker_ver = _check_docker()
    compose_avail, compose_ver = _check_compose()
    cli_installed, cli_ver = _check_cli()
    sdk_installed, sdk_ver = _check_sdk()
    pipx_avail = _check_pipx()
    mcp_present, mcp_path = _check_mcp_config()

    runtime_running = False
    runtime_reachable = False
    runtime_ver = ""

    if not skip_runtime_check and runtime_url:
        runtime_running, runtime_reachable, runtime_ver = _check_runtime(
            runtime_url
        )

    # Probe MCP boundary — use explicit URL, then env var, then SDK default
    probe_url = mcp_url or os.environ.get("KEYHOLE_MCP_URL", "")
    if not probe_url:
        try:
            from keyhole_sdk.config import DEFAULT_BASE_URL
            probe_url = DEFAULT_BASE_URL
        except ImportError:
            probe_url = ""

    boundary_reachable, contract_ver, operations = _check_mcp_boundary(
        probe_url
    )

    return EnvironmentFacts(
        platform=plat,
        python_available=True,  # we are running Python right now
        python_version=py_version,
        python_version_tuple=py_tuple,
        docker_available=docker_avail,
        docker_version=docker_ver,
        compose_available=compose_avail,
        compose_version=compose_ver,
        cli_installed=cli_installed,
        cli_version=cli_ver,
        sdk_installed=sdk_installed,
        sdk_version=sdk_ver,
        runtime_running=runtime_running,
        runtime_reachable=runtime_reachable,
        runtime_url=runtime_url,
        runtime_version=runtime_ver,
        mcp_config_present=mcp_present,
        mcp_config_path=mcp_path,
        mcp_boundary_reachable=boundary_reachable,
        mcp_boundary_url=probe_url if boundary_reachable else "",
        mcp_contract_version=contract_ver,
        mcp_operations=operations,
        pipx_available=pipx_avail,
        is_wsl=is_wsl,
        os_family=os_family,
        shell=shell,
    )


def build_facts_from_overrides(**overrides: object) -> EnvironmentFacts:
    """Build EnvironmentFacts from explicit values (for testing)."""
    return EnvironmentFacts(**overrides)  # type: ignore[arg-type]
