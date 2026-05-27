"""`keyhole workspace` — workspace lifecycle commands.

SDK-CLIENT-PUBLIC-REPAIR-01

Surfaces workspace provision through the MCP boundary:
  workspace provision --repo <name> --gap-id <id>

``--claim-token`` is optional.  The server authorizes workspace.provision
by verifying the JWT caller (``sub``) matches ``gap.claimed_by``.  Pass
``--claim-token`` only if you have one available (e.g. from an out-of-band
source); when omitted the server performs identity-bound authorization
directly.

Expected server response on success:
  {"status": "ok", "workspace_id": "...", "repo": "...", "gap_id": "..."}

Error classes surfaced from the server:
  GAP_NOT_FOUND        — gap_id does not exist
  GAP_NOT_CLAIMED      — gap is not in CLAIMED state
  CLAIM_EXPIRED        — claim window has elapsed; re-run gaps.claim
  CLAIM_OWNER_MISMATCH — JWT caller is not the claim holder
  INVALID_PARAMETERS   — malformed request shape
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token
from keyhole_sdk.run_dispatch.dispatcher import dispatch_run, OutcomeStatus
from keyhole_sdk.run_dispatch.request_builder import build_run_request
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    CommandResult,
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
)
from keyhole_sdk.config import DEFAULT_BASE_URL


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _build_transport(
    mcp_url: str, keyhole_home: str
) -> tuple[GovernedTransport, CredentialStore]:
    store_dir = Path(keyhole_home) if keyhole_home else None
    cred_store = CredentialStore(store_dir=store_dir)
    try:
        token = get_fresh_token()
    except (FileNotFoundError, RuntimeError):
        token = ""
    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth_provider)
    return transport, cred_store


def _repo_name_from_dir(repo_path: Path) -> str:
    keyhole_yaml = repo_path / "keyhole.yaml"
    if keyhole_yaml.exists():
        try:
            import yaml
            data = yaml.safe_load(keyhole_yaml.read_text(encoding="utf-8"))
            return (data or {}).get("name", repo_path.name)
        except Exception:
            pass
    return repo_path.name


# ──────────────────────────────────────────────────────────────
# keyhole workspace provision
# ──────────────────────────────────────────────────────────────

def run_workspace_provision(
    *,
    repo: str,
    gap_id: str,
    claim_token: Optional[str] = None,
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole workspace provision``.

    Provisions a governed workspace binding for a claimed gap.
    Calls run_type=workspace.provision through the MCP boundary.

    The server authorizes the request by verifying the JWT caller matches
    ``gap.claimed_by`` — ``claim_token`` is optional.  Only include it if
    you have one available from an out-of-band source.

    Required inputs:
      --repo    The public repo name (e.g. my-first-public-app)
      --gap-id  The gap_id of a gap you currently hold the claim on

    Optional inputs:
      --claim-token  Claim token (not required; JWT authorization is sufficient)

    Expected success response:
      {"status": "ok", "workspace_id": "...", "repo": "...", "gap_id": "..."}
    """
    command_label = "keyhole workspace provision"

    # ── Validate inputs ──
    missing = []
    if not repo or not repo.strip():
        missing.append("--repo")
    if not gap_id or not gap_id.strip():
        missing.append("--gap-id")

    if missing:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Missing required arguments: {', '.join(missing)}",
            next_steps=[
                "Run: keyhole gaps list — to see available gaps.",
                "Run: keyhole gaps claim --gap-id <id> — to claim a gap.",
                f"Then: {command_label} --repo <name> --gap-id <id>",
            ],
        )

    # ── Auth check ──
    store_dir = Path(keyhole_home) if keyhole_home else None
    cred_store = CredentialStore(store_dir=store_dir)
    session = cred_store.load()
    if not session or not session.access_token:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            summary="Not authenticated. Run: keyhole login",
            next_steps=["keyhole login", f"Then: {command_label}"],
        )

    try:
        token = get_fresh_token()
    except (FileNotFoundError, RuntimeError):
        token = session.access_token
    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth_provider)

    repo_path = Path(repo_dir).resolve()
    correlation_id = generate_request_id()
    input_data: Dict[str, Any] = {
        "repo": repo.strip(),
        "gap_id": gap_id.strip(),
    }
    if claim_token and claim_token.strip():
        input_data["claim_token"] = claim_token.strip()

    request = build_run_request(
        run_type="workspace.provision",
        repo_name=_repo_name_from_dir(repo_path),
        context_ref=None,
        input_data=input_data,
        correlation_id=correlation_id,
    )

    try:
        outcome = dispatch_run(transport=transport, request=request)
    finally:
        transport.close()

    if outcome.status == OutcomeStatus.SUCCESS:
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary="Workspace provisioned.",
            data=outcome.response_data,
        )

    if outcome.status == OutcomeStatus.ACCEPTED:
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Workspace provision accepted. run_id={outcome.run_id}",
            data={
                "status": "ACCEPTED",
                "run_id": outcome.run_id,
                "run_type": "workspace.provision",
            },
        )

    # Rejected — surface server message honestly
    reason = outcome.reason or "workspace.provision rejected by server."
    error_class = outcome.error_class or "unknown"

    next_steps: list[str] = outcome.repair_guidance or []
    if error_class == "GAP_NOT_FOUND":
        next_steps = [
            "Confirm the gap_id is correct: keyhole gaps list",
        ] + next_steps
    elif error_class == "GAP_NOT_CLAIMED":
        next_steps = [
            "The gap is not currently in CLAIMED state.",
            "Run: keyhole gaps claim --gap-id <id> — to claim the gap first.",
        ] + next_steps
    elif error_class == "CLAIM_EXPIRED":
        next_steps = [
            "Your claim window elapsed. Re-claim and provision immediately:",
            "Run: keyhole gaps claim --gap-id <id>",
            f"Then immediately: {command_label} --repo <name> --gap-id <id>",
        ] + next_steps
    elif error_class == "CLAIM_OWNER_MISMATCH":
        next_steps = [
            "This gap is claimed by a different user.",
            "Wait for the claim to expire or ask the claim holder to release it.",
        ] + next_steps
    elif error_class == "INVALID_PARAMETERS":
        next_steps = [
            "Confirm the repo name matches the name registered during gaps submit.",
            "Confirm the gap_id is correct: keyhole gaps list",
        ] + next_steps
    elif error_class in ("BINDING_NOT_FOUND", "NO_ENABLED_BINDING"):
        next_steps = [
            "Workspace provision requires an enabled binding for your cohort.",
            "Contact your Keyhole operator to enable workspace.provision for this tenant.",
            "Check: keyhole context compile — to confirm binding status.",
        ] + next_steps

    return CommandResult(
        command=command_label,
        success=False,
        exit_code=EXIT_FAILURE,
        summary=reason,
        data={
            "error_class": error_class,
            "run_type": "workspace.provision",
            "http_status": outcome.http_status,
        },
        next_steps=next_steps,
    )
