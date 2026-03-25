"""`keyhole verify` — verification completion command.

Implements §8.2 of DEV-SDK-00: `keyhole verify` command.

Flow:
  1. Submit verification code/token to the MCP boundary
  2. Record proof events
  3. Return structured result — never claim active before server confirms
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.onboarding.client import OnboardingClient
from keyhole_sdk.onboarding.errors import OnboardingError
from keyhole_sdk.onboarding.models import VerificationRequest
from keyhole_sdk.onboarding.proof import OnboardingProofBundle


def _resolve_proof_dir() -> Path:
    """Resolve KEYHOLE_HOME for proof bundle output."""
    keyhole_home = os.environ.get("KEYHOLE_HOME")
    if keyhole_home:
        return Path(keyhole_home)
    return Path.home() / ".keyhole"


def run_verify(
    *,
    registration_id: str,
    code: str = "",
    token: str = "",
    mcp_url: str = "https://mcp.keyholesolution.com",
) -> CommandResult:
    """Execute the verification flow and return a structured result."""
    correlation_id = str(uuid.uuid4())
    proof = OnboardingProofBundle(correlation_id=correlation_id)

    if not code and not token:
        return CommandResult(
            command="verify",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": "missing_verification_artifact"},
            summary="Either --code or --token is required for verification.",
            next_steps=[
                "keyhole verify --registration-id <id> --code <code>",
                "keyhole verify --registration-id <id> --token <token>",
            ],
        )

    request = VerificationRequest(
        registration_id=registration_id,
        code=code or None,
        token=token or None,
    )

    proof.record_event("verification_initiated", {
        "registration_id": registration_id,
        "has_code": bool(code),
        "has_token": bool(token),
        "correlation_id": correlation_id,
    })

    client = OnboardingClient(mcp_base_url=mcp_url)

    try:
        response = client.verify(request, correlation_id=correlation_id)
    except OnboardingError as exc:
        proof.record_event("verification_failed", {
            "error_class": exc.error_class,
            "reason": exc.reason,
        })

        try:
            proof.write(success=False, output_dir=_resolve_proof_dir())
        except Exception:
            pass

        return CommandResult(
            command="verify",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "correlation_id": correlation_id,
                "registration_id": registration_id,
                "error_class": exc.error_class,
                "reason": exc.reason,
            },
            summary=str(exc),
            next_steps=exc.repair_suggestions or ["Retry: keyhole verify --help"],
        )

    proof.record_event("verification_completed", response.safe_summary())

    # Write proof with verification result
    ver_summary = response.safe_summary()
    _ACTIVE_STATES = ("active", "verified", "activation_ready", "verified_active")
    try:
        proof.write(
            verification=ver_summary,
            success=response.state.value in _ACTIVE_STATES,
            output_dir=_resolve_proof_dir(),
        )
    except Exception:
        pass

    data = {
        "correlation_id": correlation_id,
        "registration_id": response.registration_id,
        "state": response.state.value,
        "user_id": response.user_id,
        "username": response.username,
        "realm": response.realm,
    }

    next_steps = []
    if response.next_step:
        next_steps.append(response.next_step)
    if response.state.value in ("active", "verified", "activation_ready"):
        next_steps.append("keyhole login")
    else:
        next_steps.append(
            f"keyhole registration-status --registration-id {response.registration_id}"
        )

    return CommandResult(
        command="verify",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=data,
        summary=f"Verification completed (state: {response.state.value})",
        next_steps=next_steps,
    )
