"""`keyhole connection whoami` — inspect connection identity (§9.3).

SDK-CLIENT-01-C: Query the server's connection-truth surface for
a specific host or connection.
"""
from __future__ import annotations

import uuid

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.connection_identity.client import ConnectionIdentityClient
from keyhole_sdk.connection_identity.errors import (
    ConnectionIdentityError,
    ConnectionNetworkError,
    ConnectionNotFoundError,
)

from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS
from keyhole_sdk.config import DEFAULT_BASE_URL


def run_connection_whoami(
    *,
    host: str = "",
    connection_id: str = "",
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """Inspect identity for a connection or host (§9.3)."""
    correlation_id = str(uuid.uuid4())

    if not host and not connection_id:
        return CommandResult(
            command="connection_whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "invalid_input",
                "correlation_id": correlation_id,
            },
            summary="Provide --host or --connection-id.",
            next_steps=[
                "keyhole connection whoami --host vscode",
                "keyhole connection whoami --connection-id <id>",
            ],
        )

    # 1. Auth check
    store = CredentialStore()
    session = store.load()
    if session is None:
        return CommandResult(
            command="connection_whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "connection_not_authenticated",
                "correlation_id": correlation_id,
            },
            summary="Not authenticated.",
            next_steps=["Run 'keyhole login' first."],
        )

    # 2. Query connection truth
    client = ConnectionIdentityClient(mcp_base_url=mcp_url)
    try:
        info = client.connection_whoami(
            access_token=session.access_token,
            host_id=host,
            connection_id=connection_id,
            correlation_id=correlation_id,
        )
    except ConnectionNotFoundError as exc:
        return CommandResult(
            command="connection_whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": exc.error_class,
                "reason": exc.reason,
                "host": host,
                "connection_id": connection_id,
                "correlation_id": correlation_id,
            },
            summary=str(exc),
            next_steps=exc.repair_suggestions,
        )
    except ConnectionNetworkError as exc:
        return CommandResult(
            command="connection_whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": exc.error_class,
                "reason": exc.reason,
                "correlation_id": correlation_id,
            },
            summary=f"Network error: {exc}",
            next_steps=exc.repair_suggestions,
        )
    except ConnectionIdentityError as exc:
        return CommandResult(
            command="connection_whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": exc.error_class,
                "reason": exc.reason,
                "correlation_id": correlation_id,
            },
            summary=str(exc),
            next_steps=exc.repair_suggestions,
        )

    return CommandResult(
        command="connection_whoami",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            **info.to_dict(),
            "correlation_id": correlation_id,
        },
        summary=(
            f"Connection principal: {info.principal} "
            f"(authority: {info.authority.value}, "
            f"staleness: {info.staleness_state.value})"
        ),
    )
