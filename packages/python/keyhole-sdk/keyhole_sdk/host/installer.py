"""SDK-CLIENT-01-D — Host credential installer (§2).

Writes or updates Keyhole MCP server entries into IDE host config files.
Supports VS Code, JetBrains (partial), and Cloud Code (partial).

Architecture invariants:
  INV-SDK-CLIENT-01-D-001: CLI is provisioner, NOT proxy.
    Hosts connect directly to MCP boundary after install.
  INV-SDK-CLIENT-01-D-002: Split identity must be explicit.
    Installation does not silently overwrite existing entries.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from keyhole_sdk.config import DEFAULT_BASE_URL
from keyhole_sdk.doctor.models import HostFamily, ReconnectRequirement


@dataclass
class HostInstallResult:
    """Outcome of a host credential installation."""

    host_family: HostFamily
    success: bool
    config_path: str = ""
    action_taken: str = ""  # "created", "updated", "skipped"
    reconnect_requirement: ReconnectRequirement = ReconnectRequirement.NONE
    previous_entry_existed: bool = False
    previous_url: str = ""
    error: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host_family": self.host_family.value,
            "success": self.success,
            "config_path": self.config_path,
            "action_taken": self.action_taken,
            "reconnect_requirement": self.reconnect_requirement.value,
            "previous_entry_existed": self.previous_entry_existed,
            "previous_url": self.previous_url,
            "error": self.error,
            "warnings": self.warnings,
        }


# ── VS Code Installer ────────────────────────────────────


_VSCODE_SETTINGS_CANDIDATES: List[str] = [
    # Linux VS Code Server (remote SSH) — most common dev scenario
    "~/.vscode-server/data/User/settings.json",
    # Linux desktop
    "~/.config/Code/User/settings.json",
    # macOS
    "~/Library/Application Support/Code/User/settings.json",
    # Insiders
    "~/.config/Code - Insiders/User/settings.json",
    "~/.vscode-server-insiders/data/User/settings.json",
]


def _find_vscode_settings() -> Optional[Path]:
    """Find the first existing VS Code settings.json."""
    for raw in _VSCODE_SETTINGS_CANDIDATES:
        p = Path(os.path.expanduser(raw))
        if p.is_file():
            return p
    # Fall back to creating in the first candidate's directory
    for raw in _VSCODE_SETTINGS_CANDIDATES:
        p = Path(os.path.expanduser(raw))
        if p.parent.is_dir():
            return p
    return None


def _build_keyhole_server_entry(
    *,
    mcp_url: str,
    server_name: str = "keyhole",
) -> Dict[str, Any]:
    """Build a VS Code MCP server entry.

    INV-SDK-CLIENT-01-D-001: Does NOT embed tokens.
    Uses env var reference for auth so the host connects directly.
    """
    return {
        "type": "sse",
        "url": mcp_url.rstrip("/") + "/mcp/v1",
        "env": {
            "KEYHOLE_MCP_TOKEN": "${env:KEYHOLE_MCP_TOKEN}",
        },
    }


def install_vscode(
    *,
    mcp_url: str = DEFAULT_BASE_URL,
    server_name: str = "keyhole",
    force: bool = False,
) -> HostInstallResult:
    """Install or update a Keyhole MCP server entry in VS Code settings.

    Does NOT embed raw tokens. Uses env var reference.
    """
    settings_path = _find_vscode_settings()
    if settings_path is None:
        return HostInstallResult(
            host_family=HostFamily.VSCODE,
            success=False,
            error="No VS Code settings directory found.",
        )

    result = HostInstallResult(
        host_family=HostFamily.VSCODE,
        success=False,
        config_path=str(settings_path),
        reconnect_requirement=ReconnectRequirement.RELOAD_WINDOW,
    )

    # Read existing settings
    if settings_path.is_file():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            result.error = f"Cannot parse settings: {exc}"
            return result
    else:
        data = {}

    if not isinstance(data, dict):
        result.error = "settings.json is not a JSON object."
        return result

    # Ensure mcp.servers key exists
    mcp_servers = data.setdefault("mcp.servers", {})
    if not isinstance(mcp_servers, dict):
        # Existing key is not a dict — cannot safely modify
        result.error = "'mcp.servers' exists but is not a JSON object."
        return result

    # Check for existing entry
    existing = mcp_servers.get(server_name)
    if existing is not None:
        result.previous_entry_existed = True
        if isinstance(existing, dict):
            result.previous_url = existing.get("url", "")

        if not force:
            result.action_taken = "skipped"
            result.success = True
            result.warnings.append(
                f"Existing '{server_name}' entry preserved. Use --force to overwrite."
            )
            return result

    # Write the entry
    entry = _build_keyhole_server_entry(mcp_url=mcp_url, server_name=server_name)
    mcp_servers[server_name] = entry
    data["mcp.servers"] = mcp_servers

    # Backup before writing
    if settings_path.is_file():
        backup = settings_path.with_suffix(".json.keyhole-backup")
        try:
            shutil.copy2(settings_path, backup)
        except OSError:
            result.warnings.append("Could not create backup of settings.json.")

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        result.error = f"Failed to write settings: {exc}"
        return result

    result.success = True
    result.action_taken = "updated" if result.previous_entry_existed else "created"
    return result


# ── JetBrains Installer (partial) ────────────────────────


def install_jetbrains(
    *,
    mcp_url: str = DEFAULT_BASE_URL,
    server_name: str = "keyhole",
    force: bool = False,
) -> HostInstallResult:
    """Install Keyhole MCP entry for JetBrains IDEs (partial support)."""
    import glob

    patterns = [
        "~/.config/JetBrains/IntelliJIdea*/",
        "~/.config/JetBrains/PyCharm*/",
        "~/.config/JetBrains/WebStorm*/",
        "~/.config/JetBrains/GoLand*/",
    ]

    config_dir: Optional[Path] = None
    for pattern in patterns:
        expanded = os.path.expanduser(pattern)
        matches = sorted(glob.glob(expanded), reverse=True)
        for m in matches:
            p = Path(m)
            if p.is_dir():
                config_dir = p
                break
        if config_dir:
            break

    if config_dir is None:
        return HostInstallResult(
            host_family=HostFamily.JETBRAINS,
            success=False,
            error="No JetBrains config directory found.",
        )

    mcp_file = config_dir / "mcp.json"
    result = HostInstallResult(
        host_family=HostFamily.JETBRAINS,
        success=False,
        config_path=str(mcp_file),
        reconnect_requirement=ReconnectRequirement.RESTART_IDE,
    )

    if mcp_file.is_file():
        try:
            data = json.loads(mcp_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            result.error = f"Cannot parse mcp.json: {exc}"
            return result
    else:
        data = {}

    if not isinstance(data, dict):
        result.error = "mcp.json is not a JSON object."
        return result

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        result.error = "'mcpServers' exists but is not a JSON object."
        return result

    existing = servers.get(server_name)
    if existing is not None:
        result.previous_entry_existed = True
        if isinstance(existing, dict):
            result.previous_url = existing.get("url", "")
        if not force:
            result.action_taken = "skipped"
            result.success = True
            result.warnings.append(
                f"Existing '{server_name}' entry preserved. Use --force to overwrite."
            )
            return result

    servers[server_name] = {
        "url": mcp_url.rstrip("/") + "/mcp/v1",
        "env": {
            "KEYHOLE_MCP_TOKEN": "${env:KEYHOLE_MCP_TOKEN}",
        },
    }
    data["mcpServers"] = servers

    try:
        mcp_file.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        result.error = f"Failed to write mcp.json: {exc}"
        return result

    result.success = True
    result.action_taken = "updated" if result.previous_entry_existed else "created"
    return result


# ── Dispatcher ────────────────────────────────────────────


_INSTALLERS = {
    HostFamily.VSCODE: install_vscode,
    HostFamily.JETBRAINS: install_jetbrains,
}


def install_host_credentials(
    *,
    host_family: HostFamily,
    mcp_url: str = DEFAULT_BASE_URL,
    server_name: str = "keyhole",
    force: bool = False,
) -> HostInstallResult:
    """Install Keyhole MCP credentials into a specific host family.

    INV-SDK-CLIENT-01-D-001: CLI is provisioner, NOT proxy.
    The installed entry directs the host to connect directly to the
    MCP boundary — never through the CLI.
    """
    installer = _INSTALLERS.get(host_family)
    if installer is None:
        return HostInstallResult(
            host_family=host_family,
            success=False,
            error=f"No installer available for host family '{host_family.value}'.",
        )
    return installer(mcp_url=mcp_url, server_name=server_name, force=force)
