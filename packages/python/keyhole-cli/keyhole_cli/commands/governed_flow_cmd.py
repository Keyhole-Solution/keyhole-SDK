"""CLI adapter for the generic governed repository flow."""
from __future__ import annotations

import os
from pathlib import Path

from keyhole_cli.result import CommandResult, EXIT_FAILURE, EXIT_SUCCESS
from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token
from keyhole_sdk.config import DEFAULT_BASE_URL
from keyhole_sdk.governed_demo import GovernedDemoError, _redact
from keyhole_sdk.governed_flow import GovernedRepoFlowClient, read_repo_declaration


def run_governed_flow(
    *,
    repo_dir: str = ".",
    story_id: str = "",
    capability_id: str = "",
    repo_class: str = "",
    gap_id: str = "",
    dry_run: bool = False,
    no_live: bool = False,
    explain: bool = False,
    mcp_url: str = DEFAULT_BASE_URL,
    runtime_url: str = "http://localhost:8080",
) -> CommandResult:
    try:
        if no_live:
            declaration = read_repo_declaration(
                Path(repo_dir).resolve(),
                story_id=story_id,
                capability_id=capability_id,
                repo_class=repo_class,
            )
            return CommandResult(
                command="keyhole governed run",
                success=True,
                exit_code=EXIT_SUCCESS,
                summary="Governed repo declaration validated locally; MCP was not mutated.",
                data=_redact({
                    "no_live": True,
                    "would_mutate_mcp": False,
                    "repo_name": declaration.repo_name,
                    "repo_remote": declaration.repo_remote,
                    "commit_sha": declaration.commit_sha,
                    "branch": declaration.branch,
                    "repo_class": declaration.repo_class,
                    "story_id": declaration.story_id,
                    "capability_id": declaration.capability_id,
                    "declaration_file_digests": declaration.declaration_file_digests,
                    "explain": "local declaration inspection only" if explain else "",
                }),
            )
        client = _client(
            mcp_url=mcp_url,
            runtime_url=runtime_url,
            story_id=story_id,
            capability_id=capability_id,
            repo_class=repo_class,
            gap_id=gap_id,
        )
        result = client.run_governed_repo_flow(repo_dir, dry_run=dry_run)
        if explain:
            result["explain"] = {
                "gap_id_source": result.get("gap_id_source", ""),
                "story_id_is_label_only": True,
                "dry_run": dry_run,
            }
        return CommandResult(
            command="keyhole governed run",
            success=True,
            exit_code=EXIT_SUCCESS,
            summary="Governed repo flow completed." if not dry_run else "Governed repo flow dry-run completed.",
            data=_redact(result),
        )
    except GovernedDemoError as exc:
        return _failure("keyhole governed run", exc, is_local=no_live)


def run_governed_status(
    *,
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    runtime_url: str = "http://localhost:8080",
) -> CommandResult:
    try:
        client = _client(mcp_url=mcp_url, runtime_url=runtime_url)
        state = client.status_governed_repo_flow(repo_dir)
        return CommandResult(
            command="keyhole governed status",
            success=True,
            exit_code=EXIT_SUCCESS,
            summary="Governed run status loaded.",
            data=state,
        )
    except GovernedDemoError as exc:
        return _failure("keyhole governed status", exc)


def run_governed_resume(
    *,
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    runtime_url: str = "http://localhost:8080",
) -> CommandResult:
    try:
        client = _client(mcp_url=mcp_url, runtime_url=runtime_url)
        result = client.resume_governed_repo_flow(repo_dir)
        return CommandResult(
            command="keyhole governed resume",
            success=True,
            exit_code=EXIT_SUCCESS,
            summary="Governed repo flow resumed.",
            data=_redact(result),
        )
    except GovernedDemoError as exc:
        return _failure("keyhole governed resume", exc)


def run_governed_receipt(
    *,
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    runtime_url: str = "http://localhost:8080",
) -> CommandResult:
    try:
        client = _client(mcp_url=mcp_url, runtime_url=runtime_url)
        result = client.receipt_governed_repo_flow(repo_dir)
        return CommandResult(
            command="keyhole governed receipt",
            success=True,
            exit_code=EXIT_SUCCESS,
            summary="Governed receipt loaded.",
            data=result,
        )
    except GovernedDemoError as exc:
        return _failure("keyhole governed receipt", exc)


def _client(
    *,
    mcp_url: str,
    runtime_url: str,
    story_id: str = "",
    capability_id: str = "",
    repo_class: str = "",
    gap_id: str = "",
) -> GovernedRepoFlowClient:
    return GovernedRepoFlowClient(
        mcp_url=mcp_url,
        token=_token(),
        runtime_url=os.environ.get("KEYHOLE_RUNTIME_URL", runtime_url),
        story_id=story_id,
        capability_id=capability_id,
        repo_class=repo_class,
        gap_id=gap_id,
    )


def _token() -> str:
    token = os.environ.get("KEYHOLE_MCP_TOKEN", "")
    if token:
        return token
    try:
        return get_fresh_token()
    except Exception as exc:
        raise GovernedDemoError(
            "KEYHOLE_MCP_TOKEN is not set and no usable device-login credential is available: "
            f"{exc}"
        ) from exc


def _failure(command: str, exc: Exception, *, is_local: bool = False) -> CommandResult:
    return CommandResult(
        command=command,
        success=False,
        exit_code=EXIT_FAILURE,
        summary=str(exc),
        data={"error_class": type(exc).__name__, "is_local": is_local},
        next_steps=[
            "Run keyhole login --flow device --force if live MCP credentials are missing.",
            "Use keyhole governed status --repo-dir <path> --last --json to inspect saved state.",
        ],
    )
