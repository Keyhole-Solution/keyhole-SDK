"""`keyhole connection invalidate` — invalidate a stale connection (§9.5).

SDK-CLIENT-01-C: Explicit governed invalidation of a stale or
wrong-principal host connection.

INV-SDK-CLIENT-01-C-006: Invalidate is idempotent.
"""
from __future__ import annotations

import uuid

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.connection_identity.client import ConnectionIdentityClient
from keyhole_sdk.connection_identity.errors import (
    ConnectionIdentityError,
    ConnectionNetworkError,
)
from keyhole_sdk.connection_identity.models import InvalidateRequest, InvalidateStatus
from keyhole_sdk.doctor.proof import DoctorProofBundle

from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS
from keyhole_sdk.config import DEFAULT_BASE_URL


def run_connection_invalidate(
    *,
    host: str = "",
    connection_id: str = "",
    yes: bool = False,
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """Invalidate a stale host connection (§9.5).

    INV-SDK-CLIENT-01-C-004: Must verify post-fix against server truth.
    INV-SDK-CLIENT-01-C-006: Uses idempotent dispatch semantics.
    """
    correlation_id = str(uuid.uuid4())
    proof = DoctorProofBundle(correlation_id=correlation_id)

    if not host and not connection_id:
        return CommandResult(
            command="connection_invalidate",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": "invalid_input", "correlation_id": correlation_id},
            summary="Provide --host or --connection-id.",
            next_steps=["keyhole connection invalidate --host vscode --yes"],
        )

    # 1. Auth check
    store = CredentialStore()
    session = store.load()
    if session is None:
        return CommandResult(
            command="connection_invalidate",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": "connection_not_authenticated", "correlation_id": correlation_id},
            summary="Not authenticated.",
            next_steps=["Run 'keyhole login' first."],
        )

    # 2. Confirmation gate
    if not yes:
        return CommandResult(
            command="connection_invalidate",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error_class": "confirmation_required",
                "host": host,
                "connection_id": connection_id,
                "correlation_id": correlation_id,
            },
            summary=(
                "Invalidation requires confirmation. "
                "Use --yes to confirm."
            ),
            next_steps=[
                f"keyhole connection invalidate --host {host or connection_id} --yes"
            ],
        )

    # 3. Build request and dispatch
    request = InvalidateRequest(
        connection_id=connection_id,
        host_id=host,
        correlation_id=correlation_id,
    )

    proof.record_event("invalidate_request", request.to_proof_dict())

    client = ConnectionIdentityClient(mcp_base_url=mcp_url)
    try:
        outcome = client.invalidate(request, access_token=session.access_token)
    except ConnectionNetworkError as exc:
        return CommandResult(
            command="connection_invalidate",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": exc.error_class, "reason": exc.reason, "correlation_id": correlation_id},
            summary=f"Network error: {exc}",
            next_steps=exc.repair_suggestions,
        )
    except ConnectionIdentityError as exc:
        return CommandResult(
            command="connection_invalidate",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": exc.error_class, "reason": exc.reason, "correlation_id": correlation_id},
            summary=str(exc),
            next_steps=exc.repair_suggestions,
        )

    proof.record_event("invalidate_outcome", outcome.safe_summary())

    is_success = outcome.status in (InvalidateStatus.ACCEPTED, InvalidateStatus.ALREADY_INVALIDATED)

    # 4. Write proof artifacts
    try:
        proof.write(
            report=outcome.to_dict(),
            requested_fix={"action": "invalidate", "host_id": host, "connection_id": connection_id},
            success=is_success,
        )
    except Exception:
        pass  # proof write is non-fatal

    # 5. Build result
    status_icons = {
        InvalidateStatus.ACCEPTED: "✓",
        InvalidateStatus.ALREADY_INVALIDATED: "↻",
        InvalidateStatus.REJECTED: "✗",
    }
    icon = status_icons.get(outcome.status, "?")

    next_steps = []
    if is_success and outcome.reconnect_required:
        next_steps.append("Reconnect the host under the desired profile.")
        next_steps.append("keyhole connections list")
    elif not is_success:
        next_steps.extend(outcome.repair_guidance)

    return CommandResult(
        command="connection_invalidate",
        success=is_success,
        exit_code=EXIT_SUCCESS if is_success else EXIT_FAILURE,
        data={
            "status": outcome.status.value,
            "connection_id": outcome.connection_id,
            "reconnect_required": outcome.reconnect_required,
            "run_id": outcome.run_id,
            "correlation_id": correlation_id,
        },
        summary=f"{icon} Connection {outcome.status.value}.",
        next_steps=next_steps,
    )
