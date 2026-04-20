"""SDK-CLIENT-01-C — Pluggable host inventory for MCP host discovery (§11).

Detects local Keyhole-relevant hosts via file/config heuristics.
All detection is advisory — server truth outranks local hints.
"""
from __future__ import annotations

import json
import os
import platform
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from keyhole_sdk.doctor.models import (
    DoctorHostRecord,
    HostDiagnosis,
    HostType,
    StalenessState,
)


from keyhole_sdk.config import DEFAULT_BASE_URL

# ── Abstract Detector ────────────────────────────────────


class HostDetector(ABC):
    """Base class for pluggable host detection (§11)."""

    @abstractmethod
    def detect(self) -> Optional[DoctorHostRecord]:
        """Attempt to detect a host. Return None if not found."""


# ── VS Code Detector ─────────────────────────────────────


_VSCODE_SETTINGS_PATHS: List[str] = [
    # Linux desktop
    "~/.config/Code/User/settings.json",
    # Linux VS Code Server (remote SSH)
    "~/.vscode-server/data/User/settings.json",
    # macOS
    "~/Library/Application Support/Code/User/settings.json",
    # VS Code Insiders (Linux)
    "~/.config/Code - Insiders/User/settings.json",
    "~/.vscode-server-insiders/data/User/settings.json",
]

_VSCODE_MCP_PATHS: List[str] = [
    "~/.config/Code/User/globalStorage/mcp.json",
    "~/.vscode-server/data/User/globalStorage/mcp.json",
]

_KEYHOLE_INDICATORS = ("keyhole", DEFAULT_BASE_URL)


class VSCodeHostDetector(HostDetector):
    """Detect VS Code IDE with Keyhole MCP server entry (§11.1)."""

    def detect(self) -> Optional[DoctorHostRecord]:
        record = DoctorHostRecord(
            host_id="vscode",
            host_type=HostType.IDE_MCP_CLIENT,
            display_name="Visual Studio Code",
        )

        # Check if VS Code is installed
        settings_path = self._find_settings_file()
        if settings_path is None:
            return record  # detected=False by default

        record.detected = True
        record.config_detected = True

        # Look for Keyhole MCP entry in settings
        keyhole_entry = self._find_keyhole_entry(settings_path)
        if keyhole_entry is not None:
            record.keyhole_server_entry_detected = True
            record.server_url = keyhole_entry.get("url", "")

        # Check MCP-specific config files
        if not record.keyhole_server_entry_detected:
            mcp_entry = self._check_mcp_config_files()
            if mcp_entry is not None:
                record.keyhole_server_entry_detected = True
                record.server_url = mcp_entry.get("url", "")

        return record

    def _find_settings_file(self) -> Optional[Path]:
        for raw in _VSCODE_SETTINGS_PATHS:
            p = Path(os.path.expanduser(raw))
            if p.is_file():
                return p
        return None

    def _find_keyhole_entry(self, settings_path: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # VS Code MCP servers can be under various keys
        for key in ("mcp.servers", "mcpServers", "mcp"):
            servers = data.get(key)
            if isinstance(servers, dict):
                for name, entry in servers.items():
                    if self._is_keyhole_entry(name, entry):
                        return entry if isinstance(entry, dict) else {"name": name}

        return None

    def _check_mcp_config_files(self) -> Optional[Dict[str, Any]]:
        for raw in _VSCODE_MCP_PATHS:
            p = Path(os.path.expanduser(raw))
            if not p.is_file():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                servers = data.get("servers", data)
                if isinstance(servers, dict):
                    for name, entry in servers.items():
                        if self._is_keyhole_entry(name, entry):
                            return entry if isinstance(entry, dict) else {"name": name}
        return None

    @staticmethod
    def _is_keyhole_entry(name: str, entry: Any) -> bool:
        name_lower = name.lower()
        if any(ind in name_lower for ind in _KEYHOLE_INDICATORS):
            return True
        if isinstance(entry, dict):
            url = str(entry.get("url", "")).lower()
            command = str(entry.get("command", "")).lower()
            if any(ind in url for ind in _KEYHOLE_INDICATORS):
                return True
            if any(ind in command for ind in _KEYHOLE_INDICATORS):
                return True
        return False


# ── SDK Credential Context Detector ──────────────────────


class SDKCredentialDetector(HostDetector):
    """Detect local SDK credential context (§11.1)."""

    def detect(self) -> Optional[DoctorHostRecord]:
        record = DoctorHostRecord(
            host_id="sdk_local",
            host_type=HostType.SDK_RUNTIME,
            display_name="Keyhole SDK (local credentials)",
            detected=True,
        )

        cred_path = self._find_credential_file()
        if cred_path is not None and cred_path.is_file():
            record.config_detected = True
            record.local_auth_hints_present = True
        else:
            record.config_detected = False

        return record

    @staticmethod
    def _find_credential_file() -> Optional[Path]:
        home = os.environ.get("KEYHOLE_HOME")
        if home:
            return Path(home) / "credentials.json"
        return Path.home() / ".keyhole" / "credentials.json"


# ── Registry ─────────────────────────────────────────────


_DEFAULT_DETECTORS: List[HostDetector] = [
    VSCodeHostDetector(),
    SDKCredentialDetector(),
]


def detect_hosts(
    *,
    detectors: Optional[List[HostDetector]] = None,
) -> List[DoctorHostRecord]:
    """Run all host detectors and return discovered records (§11).

    Never raises — individual detector failures are caught and
    the host is reported as unsupported rather than crashing the scan.
    """
    active = detectors if detectors is not None else _DEFAULT_DETECTORS
    results: List[DoctorHostRecord] = []

    for detector in active:
        try:
            record = detector.detect()
            if record is not None:
                results.append(record)
        except Exception:
            # §11.3 — no hard failure on unknown hosts
            results.append(
                DoctorHostRecord(
                    host_id=type(detector).__name__,
                    host_type=HostType.UNKNOWN,
                    display_name=f"Unknown ({type(detector).__name__})",
                    detected=False,
                    diagnosis=HostDiagnosis.UNSUPPORTED_HOST,
                )
            )

    return results
