"""`keyhole host install` — install Keyhole MCP credentials into a host (SDK-CLIENT-01-D §2).

INV-SDK-CLIENT-01-D-001: CLI is provisioner, NOT proxy.
The installed entry directs the host to connect directly to the MCP boundary.
"""
from __future__ import annotations

from keyhole_sdk.doctor.models import HostFamily
from keyhole_sdk.host.installer import install_host_credentials
from keyhole_sdk.config import DEFAULT_BASE_URL
from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS


_HOST_FAMILY_MAP = {
    "vscode": HostFamily.VSCODE,
    "jetbrains": HostFamily.JETBRAINS,
    "cloud_code": HostFamily.CLOUD_CODE,
}


def run_host_install(
    *,
    host: str,
    mcp_url: str = DEFAULT_BASE_URL,
    server_name: str = "keyhole",
    force: bool = False,
) -> CommandResult:
    """Install Keyhole MCP credentials into a host.

    INV-SDK-CLIENT-01-D-001: CLI is provisioner, NOT proxy.
    """
    family = _HOST_FAMILY_MAP.get(host.lower())
    if family is None:
        return CommandResult(
            command="host_install",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "unsupported_host",
                "host": host,
                "available_hosts": list(_HOST_FAMILY_MAP.keys()),
            },
            summary=f"Host '{host}' is not supported for credential installation.",
            next_steps=[
                f"Supported hosts: {', '.join(_HOST_FAMILY_MAP.keys())}.",
            ],
        )

    result = install_host_credentials(
        host_family=family,
        mcp_url=mcp_url,
        server_name=server_name,
        force=force,
    )

    if not result.success:
        return CommandResult(
            command="host_install",
            success=False,
            exit_code=EXIT_FAILURE,
            data=result.to_dict(),
            summary=f"Failed to install credentials for '{host}': {result.error}",
        )

    next_steps = []
    if result.reconnect_requirement.value != "none":
        next_steps.append(
            f"Reconnect required: {result.reconnect_requirement.value}."
        )
    if result.warnings:
        next_steps.extend(result.warnings)
    next_steps.append("Run 'keyhole doctor' to verify.")

    return CommandResult(
        command="host_install",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=result.to_dict(),
        summary=f"Credentials {result.action_taken} for '{host}' at {result.config_path}.",
        next_steps=next_steps,
    )
