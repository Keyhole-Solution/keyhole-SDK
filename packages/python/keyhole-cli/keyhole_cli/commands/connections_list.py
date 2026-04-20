"""`keyhole connections list` — list visible MCP connections (§9.2).

SDK-CLIENT-01-C: Connection identity listing through the governed boundary.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.connection_identity.client import ConnectionIdentityClient
from keyhole_sdk.connection_identity.errors import (
    ConnectionIdentityError,
    ConnectionNetworkError,
)

from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS
from keyhole_sdk.config import DEFAULT_BASE_URL


def run_connections_list(
    *,
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """List visible MCP connections from the server (§9.2)."""
    correlation_id = str(uuid.uuid4())

    # 1. Auth check
    store = CredentialStore()
    session = store.load()
    if session is None:
        return CommandResult(
            command="connections_list",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "connection_not_authenticated",
                "correlation_id": correlation_id,
            },
            summary="Not authenticated.",
            next_steps=["Run 'keyhole login' first."],
        )

    # 2. List connections
    client = ConnectionIdentityClient(mcp_base_url=mcp_url)
    try:
        connections = client.list_connections(
            access_token=session.access_token,
            correlation_id=correlation_id,
        )
    except ConnectionNetworkError as exc:
        return CommandResult(
            command="connections_list",
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
            command="connections_list",
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

    # 3. Format results
    conn_dicts = [c.to_dict() for c in connections]

    return CommandResult(
        command="connections_list",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "connections": conn_dicts,
            "count": len(conn_dicts),
            "correlation_id": correlation_id,
        },
        summary=f"Found {len(conn_dicts)} connection(s).",
    )
