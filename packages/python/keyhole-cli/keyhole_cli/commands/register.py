"""`keyhole register` — identity creation command.

Implements §8.1 of SDK-CLIENT-00: `keyhole register` command.

Flow:
  1. Validate classification fields for kh-dev
  2. Submit registration to the MCP boundary
  3. Record proof events
  4. Return structured result with next-step guidance
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.onboarding.client import OnboardingClient
from keyhole_sdk.onboarding.errors import OnboardingError
from keyhole_sdk.onboarding.models import OnboardingRealm, RegistrationRequest
from keyhole_sdk.onboarding.proof import OnboardingProofBundle
from keyhole_sdk.config import DEFAULT_BASE_URL


def _resolve_proof_dir() -> Path:
    """Resolve KEYHOLE_HOME for proof bundle output."""
    keyhole_home = os.environ.get("KEYHOLE_HOME")
    if keyhole_home:
        return Path(keyhole_home)
    return Path.home() / ".keyhole"


def run_register(
    *,
    email: str,
    username: str,
    display_name: str,
    realm: str = "kh-dev",
    origin: str = "",
    purpose: str = "",
    tenant: str = "",
    org: str = "",
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """Execute the registration flow and return a structured result."""
    correlation_id = str(uuid.uuid4())
    proof = OnboardingProofBundle(correlation_id=correlation_id)

    # Resolve realm enum
    try:
        realm_enum = OnboardingRealm(realm)
    except ValueError:
        valid = ", ".join(r.value for r in OnboardingRealm)
        return CommandResult(
            command="register",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": "invalid_realm", "realm": realm},
            summary=f"Unknown realm: {realm}. Valid realms: {valid}",
            next_steps=[f"Use one of: {valid}"],
        )

    request = RegistrationRequest(
        email=email,
        username=username,
        display_name=display_name,
        realm=realm_enum,
        origin=origin or None,
        purpose=purpose or None,
        tenant=tenant or None,
        org=org or None,
    )

    proof.record_event("registration_initiated", {
        "realm": realm,
        "origin": origin or None,
        "purpose": purpose or None,
        "correlation_id": correlation_id,
    })

    client = OnboardingClient(mcp_base_url=mcp_url)

    try:
        response = client.register(request, correlation_id=correlation_id)
    except OnboardingError as exc:
        proof.record_event("registration_failed", {
            "error_class": exc.error_class,
            "reason": exc.reason,
        })

        # Write failure proof
        try:
            proof.write(success=False, output_dir=_resolve_proof_dir())
        except Exception:
            pass

        return CommandResult(
            command="register",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "correlation_id": correlation_id,
                "error_class": exc.error_class,
                "reason": exc.reason,
            },
            summary=str(exc),
            next_steps=exc.repair_suggestions or ["Retry: keyhole register --help"],
        )

    proof.record_event("registration_accepted", response.safe_summary())

    # Write success proof
    reg_summary = response.safe_summary()
    try:
        proof.write(
            registration=reg_summary,
            success=False,  # Not yet verified
            output_dir=_resolve_proof_dir(),
        )
    except Exception:
        pass

    data = {
        "correlation_id": correlation_id,
        "registration_id": response.registration_id,
        "state": response.state.value,
        "realm": response.realm.value,
        "origin": response.origin,
        "purpose": response.purpose,
        "username": response.username,
        "verification_hint": response.verification_hint,
    }

    next_steps = []
    if response.next_step:
        next_steps.append(response.next_step)
    next_steps.append(
        f"keyhole verify --registration-id {response.registration_id} --code <verification-code>"
    )
    next_steps.append(
        f"keyhole registration-status --registration-id {response.registration_id}"
    )

    return CommandResult(
        command="register",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=data,
        summary=f"Registration accepted (realm: {response.realm.value}, state: {response.state.value})",
        next_steps=next_steps,
    )
