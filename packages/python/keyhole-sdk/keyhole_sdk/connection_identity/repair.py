"""SDK-CLIENT-01-C — Connection identity repair guidance (§16).

Builds concrete, next-step-oriented repair guidance
for connection identity diagnoses.
"""
from __future__ import annotations

from typing import List

from keyhole_sdk.doctor.models import HostDiagnosis


def repair_steps_for_diagnosis(
    diagnosis: HostDiagnosis,
    *,
    host_id: str = "",
    active_profile: str = "",
) -> List[str]:
    """Return concrete repair step descriptions (§16)."""

    if diagnosis == HostDiagnosis.NOT_DETECTED:
        return [
            "Verify the host is installed.",
            "Add a Keyhole MCP server entry to the host configuration.",
            f"Rerun 'keyhole doctor' or specify the host explicitly with --host {host_id}."
            if host_id
            else "Rerun 'keyhole doctor'.",
        ]

    if diagnosis == HostDiagnosis.UNSUPPORTED_HOST:
        return [
            f"Host '{host_id}' is detected but its configuration is not readable.",
            "Consult the host documentation for MCP server configuration.",
        ]

    if diagnosis == HostDiagnosis.SURFACE_UNAVAILABLE:
        return [
            "The server does not support connection-truth surfaces.",
            "Upgrade the server to a version that supports connection.identity.inspect.",
            "Use 'keyhole whoami' for generic identity inspection.",
            "Do not assume host alignment without server confirmation.",
        ]

    if diagnosis == HostDiagnosis.STALE_CONNECTION:
        return [
            "The host connection is not visible from the server.",
            "Ensure the host has opened a Keyhole connection.",
            "Refresh the host and rerun 'keyhole connections list'.",
        ]

    if diagnosis == HostDiagnosis.SPLIT_IDENTITY:
        steps = [
            "CLI profile and host connection are executing as different principals.",
        ]
        if active_profile:
            steps.append(
                f"Run 'keyhole connection rebind --host {host_id} "
                f"--profile {active_profile}' to rebind."
            )
        steps.extend(
            [
                f"Run 'keyhole connection invalidate --host {host_id} --yes' "
                "to invalidate and reconnect.",
                "Or keep the current host identity if intentional.",
            ]
        )
        return steps

    if diagnosis == HostDiagnosis.AMBIGUOUS_CONNECTION:
        return [
            "The server returned ambiguous connection identity.",
            f"Run 'keyhole connection inspect --host {host_id}' to inspect.",
            "Retry the doctor scan.",
        ]

    # ALIGNED
    return ["No action required — host identity is aligned."]


def repair_commands_for_diagnosis(
    diagnosis: HostDiagnosis,
    *,
    host_id: str = "",
    active_profile: str = "",
) -> List[str]:
    """Return executable CLI commands for repair (§16)."""
    commands: List[str] = []

    if diagnosis == HostDiagnosis.SPLIT_IDENTITY:
        if active_profile and host_id:
            commands.append(
                f"keyhole connection rebind --host {host_id} --profile {active_profile}"
            )
        if host_id:
            commands.append(
                f"keyhole connection invalidate --host {host_id} --yes"
            )

    if diagnosis == HostDiagnosis.STALE_CONNECTION and host_id:
        commands.append("keyhole connections list")
        commands.append(
            f"keyhole connection invalidate --host {host_id} --yes"
        )

    if diagnosis in (
        HostDiagnosis.NOT_DETECTED,
        HostDiagnosis.AMBIGUOUS_CONNECTION,
        HostDiagnosis.UNSUPPORTED_HOST,
    ):
        commands.append("keyhole doctor")

    if diagnosis == HostDiagnosis.SURFACE_UNAVAILABLE:
        commands.append("keyhole whoami")

    return commands
