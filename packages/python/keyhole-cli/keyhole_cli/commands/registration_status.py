"""`keyhole registration-status` — onboarding status inspection command.

Implements §8.3 of SDK-CLIENT-00: `keyhole registration-status` command.

Flow:
  1. Query status from the MCP boundary
  2. Return structured state with realm, origin, purpose, next-best action
"""

from __future__ import annotations

import uuid

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.onboarding.client import OnboardingClient
from keyhole_sdk.onboarding.errors import OnboardingError


def run_registration_status(
    *,
    registration_id: str,
    mcp_url: str = "https://mcp.keyholesolution.com",
) -> CommandResult:
    """Query and return the current onboarding state."""
    correlation_id = str(uuid.uuid4())

    client = OnboardingClient(mcp_base_url=mcp_url)

    try:
        response = client.get_status(
            registration_id, correlation_id=correlation_id,
        )
    except OnboardingError as exc:
        return CommandResult(
            command="registration-status",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "correlation_id": correlation_id,
                "registration_id": registration_id,
                "error_class": exc.error_class,
                "reason": exc.reason,
            },
            summary=str(exc),
            next_steps=exc.repair_suggestions or ["Retry: keyhole registration-status --help"],
        )

    data = {
        "correlation_id": correlation_id,
        "registration_id": response.registration_id,
        "state": response.state.value,
        "realm": response.realm,
        "origin": response.origin,
        "purpose": response.purpose,
        "username": response.username,
        "user_id": response.user_id,
    }

    next_steps = []
    if response.next_step:
        next_steps.append(response.next_step)
    state = response.state.value
    if state == "pending_verification":
        next_steps.append(
            f"keyhole verify --registration-id {response.registration_id} --code <code>"
        )
    elif state in ("active", "verified", "activation_ready"):
        next_steps.append("keyhole login")

    return CommandResult(
        command="registration-status",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=data,
        summary=f"Registration status: {state} (realm: {response.realm or 'N/A'})",
        next_steps=next_steps,
    )
