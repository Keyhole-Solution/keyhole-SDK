"""`keyhole logout` — sign-out and auth state hygiene.

Implements SDK-CLIENT-25 §8.1 client-side sign-out:

  - revoke refresh / access tokens at the boundary (best-effort);
  - delete every local auth artifact;
  - cancel pending device-flow attempts;
  - emit a redacted diagnostic event.

After this command, the next ``keyhole login`` must behave like first
run — no stale ``initialize`` hang, no skipped login.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.config import DEFAULT_AUTH_SERVER
from keyhole_sdk.sdk_client_25.auth_state import SignOutManager, default_registry
from keyhole_sdk.sdk_client_25.diagnostics import DiagnosticRecorder


def _resolve_keyhole_home() -> Path:
    keyhole_home = os.environ.get("KEYHOLE_HOME")
    if keyhole_home:
        return Path(keyhole_home)
    return Path.home() / ".keyhole"


def _default_extra_paths(keyhole_home: Path) -> list[Path]:
    """Auth-bound artifacts to clear on sign-out (§8.1)."""
    return [
        # Cached MCP server account binding hint (extension-level).
        keyhole_home / "mcp_account.json",
        # PKCE in-flight state (if any tool persisted it).
        keyhole_home / "pkce_state.json",
        # Pending device-flow state (if any tool persisted it).
        keyhole_home / "device_flow_state.json",
        # Identity context cached from prior whoami.
        keyhole_home / "proof_bundle" / "identity_context.json",
    ]


def _resolve_revocation_endpoint(auth_server_url: str) -> str:
    """Best-effort revocation endpoint for Keycloak realms.

    SDK-SERVER-25 supports OIDC discovery; if the discovery document
    advertises ``revocation_endpoint`` we should prefer that.  But for
    sign-out we treat revocation as best-effort and avoid a blocking
    discovery round-trip — Keycloak's standard path is well known.
    """
    base = auth_server_url.rstrip("/")
    return f"{base}/protocol/openid-connect/revoke"


def run_logout(
    *,
    auth_server_url: str = DEFAULT_AUTH_SERVER,
    client_id: str = "keyhole-cli",
    skip_revocation: bool = False,
) -> CommandResult:
    """Run the sign-out command.

    Args:
        auth_server_url: OAuth issuer URL (used to derive the
            revocation endpoint).
        client_id: OAuth client_id used for revocation.
        skip_revocation: If True, only clear local state.  Useful when
            the boundary is unreachable.
    """
    correlation_id = str(uuid.uuid4())
    keyhole_home = _resolve_keyhole_home()
    log_path = keyhole_home / "diagnostics" / "auth.log"
    recorder = DiagnosticRecorder(
        log_path=log_path, correlation_id=correlation_id
    )

    credential_store = CredentialStore()
    revocation_endpoint: Optional[str] = (
        None if skip_revocation else _resolve_revocation_endpoint(auth_server_url)
    )

    manager = SignOutManager(
        credential_store=credential_store,
        registry=default_registry(),
        revocation_endpoint=revocation_endpoint,
        client_id=client_id,
        extra_paths=_default_extra_paths(keyhole_home),
        on_event=lambda name, payload: recorder.record(name, payload),
    )

    recorder.record("auth.logout.started", {
        "client_id": client_id,
        "skip_revocation": skip_revocation,
    })

    result = manager.sign_out(correlation_id=correlation_id)

    summary = (
        "Signed out — local auth state cleared."
        if result.success
        else "Signed out locally; remote revocation incomplete."
    )

    next_steps = [
        "Run: keyhole login   # to start a fresh authentication",
    ]

    warnings = []
    if not result.revoked_refresh_token and not skip_revocation:
        warnings.append(
            "Refresh token was not revoked at the boundary "
            "(best-effort revocation)."
        )
    if result.error_message:
        warnings.append(result.error_message)

    return CommandResult(
        command="logout",
        success=result.cleared_credential_store,
        exit_code=EXIT_SUCCESS if result.cleared_credential_store else EXIT_FAILURE,
        data={
            "correlation_id": correlation_id,
            "logout": result.to_safe_dict(),
            "diagnostics_path": str(log_path),
        },
        warnings=warnings,
        next_steps=next_steps,
        summary=summary,
    )
