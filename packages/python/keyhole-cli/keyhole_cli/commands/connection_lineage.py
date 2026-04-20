"""`keyhole connection lineage` — inspect connection identity lineage (§9.4).

SDK-CLIENT-01-C: Explain how the current connection identity came to be
through the governed connection.lineage.inspect run type.

INV-SDK-CLIENT-01-C-008: Surface remains governed.
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


def run_connection_lineage(
    *,
    host: str = "",
    connection_id: str = "",
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """Inspect connection identity lineage (§9.4)."""
    correlation_id = str(uuid.uuid4())

    if not host and not connection_id:
        return CommandResult(
            command="connection_lineage",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "invalid_input",
                "correlation_id": correlation_id,
            },
            summary="Provide --host or --connection-id.",
            next_steps=[
                "keyhole connection lineage --host vscode",
                "keyhole connection lineage --connection-id <id>",
            ],
        )

    # 1. Auth check
    store = CredentialStore()
    session = store.load()
    if session is None:
        return CommandResult(
            command="connection_lineage",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "connection_not_authenticated",
                "correlation_id": correlation_id,
            },
            summary="Not authenticated.",
            next_steps=["Run 'keyhole login' first."],
        )

    # 2. Query lineage via connection.lineage.inspect
    client = ConnectionIdentityClient(mcp_base_url=mcp_url)
    try:
        lineage = client.connection_lineage(
            access_token=session.access_token,
            host_id=host,
            connection_id=connection_id,
            correlation_id=correlation_id,
        )
    except ConnectionNotFoundError as exc:
        return CommandResult(
            command="connection_lineage",
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
            command="connection_lineage",
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
            command="connection_lineage",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": exc.error_class,
                "reason": exc.reason,
                "correlation_id": correlation_id,
            },
            summary=str(exc),
            next_steps=getattr(exc, "repair_suggestions", []),
        )

    return CommandResult(
        command="connection_lineage",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            **lineage,
            "correlation_id": correlation_id,
        },
        summary=f"Lineage retrieved for {host or connection_id}.",
    )
