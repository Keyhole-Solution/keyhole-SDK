"""`keyhole host inspect` — inspect a specific host's configuration (SDK-CLIENT-01-D §6).

Shows detailed configuration, auth source, and principal source for a host.
"""
from __future__ import annotations

from keyhole_sdk.doctor.host_inventory import detect_hosts
from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS


def run_host_inspect(
    *,
    host: str,
) -> CommandResult:
    """Inspect a specific host's Keyhole configuration."""
    records = detect_hosts()

    target = None
    for r in records:
        if r.host_id == host:
            target = r
            break

    if target is None:
        return CommandResult(
            command="host_inspect",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "host_not_found",
                "host": host,
                "available_hosts": [r.host_id for r in records],
            },
            summary=f"Host '{host}' not found.",
            next_steps=[
                "Run 'keyhole host list' to see available hosts.",
            ],
        )

    return CommandResult(
        command="host_inspect",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=target.to_dict(),
        summary=f"Host '{host}': detected={target.detected}, configured={target.keyhole_server_entry_detected}.",
    )
