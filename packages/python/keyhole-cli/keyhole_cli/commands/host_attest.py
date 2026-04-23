"""`keyhole host attest` — host identity attestation command (SDK-CLIENT-23 §C).

Performs a live ``whoami`` through the CLI's stored credentials
and writes a host identity attestation file to the canonical
attestation directory.

For VS Code gallery-installed hosts, this command is invoked from the
terminal while the MCP host is active. It proves the effective
principal by calling the real MCP boundary.
"""
from __future__ import annotations

import hashlib
import platform
import uuid
from datetime import datetime, timezone, timedelta

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.whoami import WhoamiClient
from keyhole_sdk.auth_bootstrap.errors import AuthBootstrapError
from keyhole_sdk.config import DEFAULT_BASE_URL
from keyhole_sdk.doctor.models import (
    ATTESTATION_TTL_SECONDS,
    AttestationConfidence,
    HostIdentityAttestation,
)
from keyhole_sdk.host.attestation_store import write_attestation

import keyhole_sdk


def _machine_scope() -> str:
    """Derive a deterministic machine scope from hostname."""
    raw = platform.node() or "unknown"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def run_host_attest(
    *,
    host_kind: str = "vscode",
    integration_name: str = "keyhole",
    server_url: str = DEFAULT_BASE_URL,
    realm: str = "kh-prod",
    workspace_scope: str | None = None,
) -> CommandResult:
    """Perform a live whoami and write a host attestation file.

    This proves which principal is currently active on the MCP boundary
    and records it as a local attestation for coherence checks.
    """
    store = CredentialStore()
    session = store.load()

    if session is None:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            summary="Not authenticated — no stored credentials found.",
            next_steps=["Run 'keyhole login' to authenticate first."],
        )

    if session.is_expired:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"expired": True},
            summary="Session expired. Cannot prove identity with expired credentials.",
            next_steps=[
                "Run 'keyhole login' to re-authenticate.",
                "Then re-run 'keyhole host attest'.",
            ],
        )

    # Perform live whoami to prove effective principal
    client = WhoamiClient(mcp_base_url=server_url)
    try:
        whoami = client.whoami(session.access_token)
    except AuthBootstrapError as exc:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": exc.error_class},
            summary=f"Could not prove identity: {exc}",
            next_steps=exc.repair_suggestions or [
                "Run 'keyhole login' to re-authenticate.",
            ],
        )
    except Exception as exc:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Failed to contact MCP boundary: {exc}",
            next_steps=[
                "Check your network connection.",
                f"Verify MCP boundary is reachable: {server_url}",
            ],
        )

    # Build the principal label
    principal = whoami.display_name or whoami.email or whoami.user_id or ""
    subject = whoami.user_id or ""

    if not principal:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            summary="whoami returned no identifiable principal.",
            next_steps=["Check your authentication state."],
        )

    # Build display name for host
    host_display_map = {
        "vscode": "VS Code",
        "jetbrains": "JetBrains",
        "cloud_code": "Cloud Code",
        "sdk_local": "SDK Local",
    }

    now = datetime.now(timezone.utc)
    correlation_id = str(uuid.uuid4())

    attestation = HostIdentityAttestation(
        schema_version="1",
        host_kind=host_kind,
        host_display_name=host_display_map.get(host_kind, host_kind),
        integration_name=integration_name,
        server_url=server_url,
        realm=realm,
        effective_principal=principal,
        effective_subject=subject,
        proof_method="live_whoami",
        confidence=AttestationConfidence.CONFIRMED,
        observed_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=ATTESTATION_TTL_SECONDS)).isoformat(),
        machine_scope=_machine_scope(),
        workspace_scope=workspace_scope,
        correlation_id=correlation_id,
        notes="Attested via CLI-bound whoami against live MCP boundary",
        tool_version=f"keyhole-host-attest/{keyhole_sdk.__version__}",
    )

    try:
        path = write_attestation(attestation)
    except Exception as exc:
        return CommandResult(
            command="host_attest",
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Failed to write attestation file: {exc}",
        )

    return CommandResult(
        command="host_attest",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "host_kind": host_kind,
            "effective_principal": principal,
            "effective_subject": subject,
            "proof_method": "live_whoami",
            "confidence": "confirmed",
            "observed_at": now.isoformat(),
            "expires_at": attestation.expires_at,
            "attestation_path": str(path),
            "correlation_id": correlation_id,
        },
        summary=(
            f"Host attestation written for {host_display_map.get(host_kind, host_kind)}: "
            f"{principal} (confirmed via live whoami)"
        ),
        next_steps=[
            "Run 'keyhole doctor' to check identity coherence.",
            "Run 'keyhole login' to bind CLI credentials.",
        ],
    )
