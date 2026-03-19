"""`keyhole whoami` — identity inspection command.

Implements §8.2 of DEV-SDK-01: `keyhole whoami` command.

Flow:
  1. Load local credential/session
  2. Call the server identity endpoint
  3. Render returned identity context
  4. Surface mode and workspace context
"""

from __future__ import annotations

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.errors import AuthBootstrapError
from keyhole_sdk.auth_bootstrap.whoami import WhoamiClient


def run_whoami(
    *,
    mcp_base_url: str = "https://api.keyhole.dev",
) -> CommandResult:
    """Load stored credentials and inspect identity via whoami."""
    store = CredentialStore()

    # Check for stored session
    session = store.load()
    if session is None:
        return CommandResult(
            command="whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            summary="Not authenticated — no stored credentials found.",
            next_steps=["Run 'keyhole login' to authenticate."],
        )

    if session.is_expired:
        return CommandResult(
            command="whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"expired": True},
            summary="Session expired.",
            next_steps=[
                "Run 'keyhole login' to re-authenticate.",
                "Run 'keyhole login --force' to force a fresh login.",
            ],
        )

    # Call whoami
    client = WhoamiClient(mcp_base_url=mcp_base_url)
    try:
        whoami = client.whoami(session.access_token)
    except AuthBootstrapError as exc:
        return CommandResult(
            command="whoami",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error_class": exc.error_class},
            summary=str(exc),
            next_steps=exc.repair_suggestions or [
                "Run 'keyhole login' to re-authenticate."
            ],
        )

    # Build identity data for display
    data = {
        "user_id": whoami.user_id,
        "tenant_id": whoami.tenant_id,
        "org_id": whoami.org_id,
        "cohort_id": whoami.cohort_id,
        "worker_id": whoami.worker_id,
        "workspace_id": whoami.workspace_id,
        "plan": whoami.plan,
        "mode": whoami.mode.value,
    }

    if whoami.display_name:
        data["display_name"] = whoami.display_name
    if whoami.roles:
        data["roles"] = whoami.roles
    if whoami.limits:
        data["limits"] = whoami.limits

    mode_label = whoami.mode.value
    next_steps = [
        "Run 'keyhole init vertical' to scaffold a governed repository.",
        "Run 'keyhole ingest .' to analyze an existing repository.",
        "Run 'keyhole validate' to validate your workspace.",
    ]

    return CommandResult(
        command="whoami",
        success=True,
        exit_code=EXIT_SUCCESS,
        data=data,
        summary=f"Identity verified (mode: {mode_label})",
        next_steps=next_steps,
    )
