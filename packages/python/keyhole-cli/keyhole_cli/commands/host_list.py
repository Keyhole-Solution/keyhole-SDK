"""`keyhole host list` — list discovered IDE hosts (SDK-CLIENT-01-D §6).

Runs the pluggable host inventory and reports what hosts are found
on this machine, along with their Keyhole configuration status.
"""
from __future__ import annotations

from keyhole_sdk.doctor.host_inventory import detect_hosts
from keyhole_cli.result import CommandResult, EXIT_SUCCESS


def run_host_list() -> CommandResult:
    """Discover and list IDE hosts on this machine."""
    records = detect_hosts()

    host_dicts = [r.to_dict() for r in records]
    detected = [r for r in records if r.detected]
    configured = [r for r in detected if r.keyhole_server_entry_detected]

    summary_parts = [
        f"{len(records)} host(s) scanned",
        f"{len(detected)} detected",
        f"{len(configured)} configured with Keyhole",
    ]

    return CommandResult(
        command="host_list",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "hosts": host_dicts,
            "total_scanned": len(records),
            "total_detected": len(detected),
            "total_configured": len(configured),
        },
        summary=", ".join(summary_parts) + ".",
    )
