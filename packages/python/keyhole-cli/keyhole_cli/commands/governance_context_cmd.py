"""`keyhole governance-context create` — bind gap to subject repo, replacing workspace.provision.

SDK-CLIENT-30: Repo-as-Workspace Governance Model

Creates a governance context that binds a claimed gap to the subject repo
without creating a server-side persistent workspace or Git branch.

This replaces the deprecated ``workspace.provision`` flow for downstream
SDK/customer/forked repo workflows.

Expected server response:
  {
    "governance_context_id": "gctx_...",
    "gap_id": "gap_...",
    "repo_binding_id": "repo_...",
    "repo_remote": "...",
    "branch": "main",
    "commit_sha": "...",
    "workspace_model": "repo_as_workspace",
    "persistent_workspace_created": false
  }

Server compatibility guards — the SDK fails loudly if:
  OBSOLETE_WORKSPACE_PROVISION_FLOW     — server asks to call workspace.provision
  PLATFORM_REPO_TARGET_FORBIDDEN        — server resolves subject repo to platform control repo
  GOVERNANCE_CONTEXT_REQUIRED           — server returns workspace_id without governance_context_id
  SUBJECT_REPO_BINDING_REQUIRED         — server response missing subject repo identity
  REPO_AS_WORKSPACE_CONTRACT_VIOLATION  — server creates a persistent workspace
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token
from keyhole_sdk.repo_identity import RepoIdentityError, detect_repo_identity
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

# The platform control repo slug — never a valid subject workspace
_PLATFORM_CONTROL_SLUG = "keyhole-solution/keyhole_platform"


def _check_server_compat(result_data: Dict[str, Any]) -> Optional[CommandResult]:
    """Apply server compatibility guards to a governance context response.

    Returns a failure CommandResult if the response violates the
    repo-as-workspace contract, or None if the response is valid.
    """
    command_label = "keyhole governance-context create"

    # Guard 1: server must not create a persistent workspace
    if result_data.get("persistent_workspace_created") is True:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=(
                "REPO_AS_WORKSPACE_CONTRACT_VIOLATION: server created a persistent "
                "workspace (persistent_workspace_created=true). For downstream repo "
                "flows, the repo IS the workspace. The server must not provision "
                "additional persistent workspaces."
            ),
            data={"error_code": "REPO_AS_WORKSPACE_CONTRACT_VIOLATION"},
            next_steps=[
                "Report this to the platform team: server-side workspace.provision "
                "was invoked for a downstream governance context request.",
            ],
        )

    # Guard 2: server must not resolve subject repo to platform control repo
    repo_remote = result_data.get("repo_remote", "") or ""
    repo_slug_raw = (
        result_data.get("repo_binding_id", "")
        or result_data.get("repo", "")
        or ""
    )
    workspace_branch = result_data.get("branch", "") or ""
    if (
        "Keyhole-Solution/keyhole_platform" in repo_remote
        or "keyhole_platform" in workspace_branch
        or "keyhole_platform" == repo_slug_raw
    ):
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=(
                "PLATFORM_REPO_TARGET_FORBIDDEN: server resolved the subject repo "
                "to Keyhole-Solution/keyhole_platform. SDK/customer workflows must "
                "never target the platform control repo."
            ),
            data={"error_code": "PLATFORM_REPO_TARGET_FORBIDDEN"},
            next_steps=[
                "The server returned a governance context pointing at the platform "
                "control repo. This is a server-side contract violation.",
                "Report this to the platform team.",
            ],
        )

    # Guard 3: server must return governance_context_id, not just workspace_id
    governance_context_id = result_data.get("governance_context_id")
    workspace_id_only = result_data.get("workspace_id") and not governance_context_id
    if workspace_id_only:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=(
                "GOVERNANCE_CONTEXT_REQUIRED: server returned workspace_id without "
                "governance_context_id. The new repo-as-workspace model requires a "
                "governance_context_id. The server may be running an older version."
            ),
            data={
                "error_code": "GOVERNANCE_CONTEXT_REQUIRED",
                "workspace_id": result_data.get("workspace_id"),
            },
            next_steps=[
                "Ensure the server supports SDK-CLIENT-30 (repo-as-workspace).",
                "If the server is older, upgrade the server-side implementation.",
            ],
        )

    # Guard 4: server must include subject repo binding in response
    if not result_data.get("repo_binding_id") and not result_data.get("repo_remote"):
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=(
                "SUBJECT_REPO_BINDING_REQUIRED: server response does not include "
                "subject repo binding (repo_binding_id or repo_remote). The governance "
                "context cannot be proven without knowing the subject repo."
            ),
            data={"error_code": "SUBJECT_REPO_BINDING_REQUIRED"},
            next_steps=[
                "The server must return repo_binding_id and repo_remote in the "
                "governance context response.",
                "Ensure the server supports SDK-CLIENT-30.",
            ],
        )

    return None  # all guards passed


# ──────────────────────────────────────────────────────────────
# Command implementation
# ──────────────────────────────────────────────────────────────


def run_governance_context_create(
    *,
    gap_id: str,
    claim_token: str,
    repo_dir: str = ".",
    repo_binding_id: str = "",
    purpose: str = "development",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole governance-context create``.

    Binds a claimed gap to the subject repo by creating a governance context.
    Does not create a server-side persistent workspace or Git branch.

    Required inputs:
      --gap-id       Gap ID (from ``keyhole gaps claim``)
      --claim-token  Claim token from ``keyhole gaps claim``

    Optional inputs:
      --repo-binding-id  Override the repo_binding_id (defaults to .keyhole/repo-binding.json)
      --purpose          Context purpose (default: development)

    Returns a CommandResult for the CLI to render.
    """
    command_label = "keyhole governance-context create"

    # ── Validate required inputs ──
    missing = []
    if not gap_id or not gap_id.strip():
        missing.append("--gap-id")
    if not claim_token or not claim_token.strip():
        missing.append("--claim-token")
    if missing:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Missing required arguments: {', '.join(missing)}",
            next_steps=[
                "Run: keyhole gaps claim --gap-id <id>",
                f"Then: {command_label} --gap-id <id> --claim-token <token>",
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

    # ── Detect local repo identity ──
    repo_path = Path(repo_dir).resolve()
    try:
        identity = detect_repo_identity(str(repo_path))
    except RepoIdentityError as exc:
        error_code = getattr(exc, "error_code", "REPO_IDENTITY_ERROR")
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=str(exc),
            data={"error_code": error_code},
            next_steps=[
                "Ensure you are inside a Git repository with an 'origin' remote.",
                "Run: keyhole repo attach — to enroll your repo.",
            ],
        )

    # Resolve repo_binding_id — prefer explicit arg, then identity-stored value
    effective_binding_id = (
        repo_binding_id.strip()
        or identity.repo_binding_id
        or ""
    )

    # ── Build request payload ──
    input_data: Dict[str, Any] = {
        "gap_id": gap_id.strip(),
        "claim_token": claim_token.strip(),
        "repo_remote": identity.repo_remote,
        "branch": identity.current_branch,
        "commit_sha": identity.commit_sha,
        "purpose": purpose or "development",
        "origin": "sdk",
    }
    if effective_binding_id:
        input_data["repo_binding_id"] = effective_binding_id

    # ── Dispatch governance.context.create ──
    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth_provider)

    request = build_run_request(
        run_type="governance.context.create",
        repo_name=identity.repo,
        context_ref=None,
        input_data=input_data,
        correlation_id=generate_request_id(),
    )

    try:
        outcome = dispatch_run(transport=transport, request=request)
    finally:
        transport.close()

    if outcome.status not in (OutcomeStatus.SUCCESS, OutcomeStatus.ACCEPTED):
        error_class = outcome.error_class or "unknown"
        reason = outcome.reason or "governance.context.create rejected by server."

        # Check for obsolete workspace.provision redirect
        if error_class == "OBSOLETE_WORKSPACE_PROVISION_FLOW" or (
            "workspace.provision" in reason
        ):
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_FAILURE,
                summary=(
                    "OBSOLETE_WORKSPACE_PROVISION_FLOW: the server returned an error "
                    "indicating use of the old workspace.provision flow. The new "
                    "repo-as-workspace model does not use workspace.provision. "
                    "Ensure the server supports SDK-CLIENT-30."
                ),
                data={"error_code": "OBSOLETE_WORKSPACE_PROVISION_FLOW"},
                next_steps=[
                    "Upgrade the server to a version supporting governance.context.create.",
                ],
            )

        next_steps: list[str] = outcome.repair_guidance or []
        if error_class == "NOT_IMPLEMENTED":
            next_steps = [
                "governance.context.create is not yet available on this server.",
                "Ensure the server supports SDK-CLIENT-30 (repo-as-workspace model).",
            ] + next_steps
        elif error_class in ("GAP_NOT_CLAIMED", "CLAIM_EXPIRED"):
            next_steps = [
                "Re-claim the gap: keyhole gaps claim --gap-id " + gap_id.strip(),
                f"Then immediately: {command_label} --gap-id {gap_id.strip()} --claim-token <new_token>",
            ] + next_steps

        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=reason,
            data={"error_class": error_class, "run_type": "governance.context.create"},
            next_steps=next_steps,
        )

    result_data: Dict[str, Any] = outcome.response_data or {}

    # ── Apply server compatibility guards ──
    compat_failure = _check_server_compat(result_data)
    if compat_failure is not None:
        return compat_failure

    governance_context_id = result_data.get("governance_context_id", "")
    workspace_model = result_data.get("workspace_model", "repo_as_workspace")
    persistent_created = result_data.get("persistent_workspace_created", False)

    summary_parts = [
        f"Gap claimed: {gap_id.strip()}",
        f"Governance context: {governance_context_id or '(pending)'}",
        f"Repo: {identity.slug}",
        f"Branch: {identity.current_branch}",
        f"Commit: {identity.commit_sha[:12]}",
        f"Workspace model: {workspace_model.replace('_', '-')}",
        f"Persistent workspace created: {'yes' if persistent_created else 'no'}",
    ]

    return CommandResult(
        command=command_label,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary="\n".join(summary_parts),
        data={
            "governance_context_id": governance_context_id,
            "gap_id": gap_id.strip(),
            "repo_binding_id": result_data.get("repo_binding_id", effective_binding_id),
            "repo_remote": identity.repo_remote,
            "branch": identity.current_branch,
            "commit_sha": identity.commit_sha,
            "workspace_model": workspace_model,
            "persistent_workspace_created": persistent_created,
        },
        next_steps=[
            "Run: keyhole verify — to run ephemeral verification against this commit.",
            "Run: keyhole proof submit — to submit evidence for governance verdict.",
        ],
    )
