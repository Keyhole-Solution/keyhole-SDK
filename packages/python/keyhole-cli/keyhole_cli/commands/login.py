"""`keyhole login` — authentication bootstrap command.

Implements §8.1 of DEV-SDK-01: `keyhole login` command.

Hardened flow (server-aligned identity governance):
  1. Initiate auth bootstrap
  2. Complete auth flow (PKCE or device)
  3. Acquire governed identity via /whoami (mandatory)
  4. Persist credentials ONLY after identity confirmed
  5. Render success ONLY after governed closure
"""

from __future__ import annotations

import uuid
from typing import Optional

import typer

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_bootstrap.client import AuthBootstrapClient
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.models import AuthFlowType, LoginResult
from keyhole_sdk.auth_bootstrap.proof import AuthProofBundle


def _resolve_proof_dir() -> "Path":
    """Resolve KEYHOLE_HOME for proof bundle output."""
    import os
    from pathlib import Path
    keyhole_home = os.environ.get("KEYHOLE_HOME")
    if keyhole_home:
        return Path(keyhole_home)
    return Path.home() / ".keyhole"


def run_login(
    *,
    flow: str = "pkce",
    force: bool = False,
    auth_server_url: str = "https://auth.keyholesolution.com/realms/keyhole-mcp",
    client_id: str = "keyhole-cli",
    mcp_base_url: str = "https://mcp.keyholesolution.com",
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> CommandResult:
    """Execute the full login flow and return a structured result."""
    correlation_id = str(uuid.uuid4())
    proof = AuthProofBundle(correlation_id=correlation_id)

    # Resolve flow type
    try:
        flow_type = AuthFlowType(flow.lower())
    except ValueError:
        return CommandResult(
            command="login",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": "invalid_flow_type", "flow": flow},
            summary=f"Unknown flow type: {flow}. Use 'pkce', 'device', or 'password'.",
            next_steps=["Use: keyhole login --flow pkce", "Or: keyhole login --flow device"],
        )

    proof.record_event("login_initiated", {
        "flow_type": flow_type.value,
        "force": force,
        "correlation_id": correlation_id,
    })

    client = AuthBootstrapClient(
        auth_server_url=auth_server_url,
        client_id=client_id,
        mcp_base_url=mcp_base_url,
    )

    status_messages: list[str] = []

    def on_status(msg: str) -> None:
        status_messages.append(msg)
        typer.echo(msg, err=True)

    def on_browser_url(url: str) -> None:
        proof.record_event("browser_url_presented", {"url_shown": True})
        typer.echo(f"\nOpen this URL in your browser to authenticate:\n  {url}\n", err=True)

    def on_device_code(device_resp) -> None:
        proof.record_event("device_code_presented", {
            "user_code": device_resp.user_code,
            "verification_uri": device_resp.verification_uri,
        })
        typer.echo(
            f"\n  Verification URL : {device_resp.verification_uri_complete or device_resp.verification_uri}"
            f"\n  User Code        : {device_resp.user_code}"
            f"\n\nVisit the URL above and enter the code to authenticate.\nWaiting...\n",
            err=True,
        )

    result = client.login(
        flow_type=flow_type,
        force=force,
        correlation_id=correlation_id,
        on_browser_url=on_browser_url,
        on_device_code=on_device_code,
        on_status=on_status,
        username=username,
        password=password,
    )

    proof.record_event("login_completed", result.safe_summary())

    if result.success:
        # Determine auth path for proof lineage
        auth_path = "session_reuse" if not force and result.credential_persisted else "device_flow"
        proof.record_event("auth_path_resolved", {"auth_path": auth_path})

        # Persist proof bundle to KEYHOLE_HOME
        try:
            proof.write(result, _resolve_proof_dir())
        except Exception:
            pass  # proof write failure is not a login failure

        return _success_result(result, proof, correlation_id, auth_path=auth_path)
    else:
        return _failure_result(result, proof, correlation_id)


def _success_result(
    result: LoginResult,
    proof: AuthProofBundle,
    correlation_id: str,
    *,
    auth_path: str = "unknown",
) -> CommandResult:
    """Build CommandResult for successful login."""
    whoami = result.whoami
    data = {
        "correlation_id": correlation_id,
        "flow_type": result.flow_type.value if result.flow_type else None,
        "mode": result.mode.value if result.mode else None,
        "auth_path": auth_path,
        "credential_persisted": result.credential_persisted,
        "verification_passed": result.verification_passed,
    }
    if whoami:
        data.update({
            "user_id": whoami.user_id,
            "tenant_id": whoami.tenant_id,
            "org_id": whoami.org_id,
            "display_name": whoami.display_name,
        })

    mode_label = result.mode.value if result.mode else "unknown"
    next_steps = [
        "Run 'keyhole whoami' to inspect your identity.",
        "Run 'keyhole init vertical' to scaffold a governed repository.",
        "Run 'keyhole ingest .' to analyze an existing repository.",
    ]

    return CommandResult(
        command="login",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=data,
        summary=f"Logged in successfully (mode: {mode_label})",
        next_steps=next_steps,
    )


def _failure_result(
    result: LoginResult,
    proof: AuthProofBundle,
    correlation_id: str,
) -> CommandResult:
    """Build CommandResult for failed login."""
    data = {
        "correlation_id": correlation_id,
        "error_class": result.error_class,
        "credential_persisted": result.credential_persisted,
        "verification_passed": result.verification_passed,
    }

    return CommandResult(
        command="login",
        success=False,
        exit_code=EXIT_FAILURE,
        data=data,
        summary=result.error_message or "Login failed",
        next_steps=result.repair_suggestions or ["Retry: keyhole login"],
    )
