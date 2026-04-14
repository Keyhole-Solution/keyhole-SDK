from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from requests import RequestException

from keyhole_sdk import KeyholeClient

from keyhole_cli.result import emit
from keyhole_cli.commands.context_cmd import run_context_compile, run_context_inspect
from keyhole_cli.commands.doctor import run_doctor
from keyhole_cli.commands.init_cmd import run_init
from keyhole_cli.commands.init_vertical import run_init_vertical
from keyhole_cli.commands.login import run_login
from keyhole_cli.commands.register import run_register
from keyhole_cli.commands.registration_status import run_registration_status
from keyhole_cli.commands.ingest_cmd import run_ingest
from keyhole_cli.commands.align_cmd import run_align
from keyhole_cli.commands.repo_register_cmd import run_repo_register
from keyhole_cli.commands.run_cmd import run_run
from keyhole_cli.commands.search_cmd import run_search
from keyhole_cli.commands.dependency_resolve_cmd import run_dependency_resolve
from keyhole_cli.commands.runs_cmd import (
    run_runs_list,
    run_runs_resume,
    run_runs_status,
    run_runs_tail,
    run_runs_wait,
)
from keyhole_cli.commands.budget_cmd import run_budget
from keyhole_cli.commands.validate_cmd import run_validate
from keyhole_cli.commands.explain_cmd import (
    run_explain_run,
    run_inspect_request,
    run_support_bundle,
)
from keyhole_cli.commands.passport_cmd import run_passport_generate, run_passport_show
from keyhole_cli.commands.capability_cmd import (
    run_capability_create,
    run_capability_validate,
)
from keyhole_cli.commands.runtime import run_start, run_stop, run_status
from keyhole_cli.commands.smoke import run_smoke
from keyhole_cli.commands.verify import run_verify
from keyhole_cli.commands.whoami import run_whoami

DEFAULT_RUNTIME_URL = "http://localhost:8080"

app = typer.Typer(
    help="Command-line interface for the Keyhole Developer Kit.",
    no_args_is_help=True,
)

runtime_app = typer.Typer(
    help="Interact with a Keyhole-compatible runtime.",
    no_args_is_help=True,
)

init_app = typer.Typer(
    help="Initialize workspaces and governed repo scaffolds.",
    invoke_without_command=True,
)

context_app = typer.Typer(
    help="Context lifecycle — compile, inspect, and manage governed context.",
    no_args_is_help=True,
)

runs_app = typer.Typer(
    help="Async run lifecycle — status, wait, tail, resume, and list.",
    no_args_is_help=True,
)

repo_app = typer.Typer(
    help="Repository management — register, status, and lifecycle.",
    no_args_is_help=True,
)

dependency_app = typer.Typer(
    help="Dependency management — resolve and inspect.",
    no_args_is_help=True,
)

explain_app = typer.Typer(
    help="Governance explainability — explain runs and inspect requests.",
    no_args_is_help=True,
)

capability_app = typer.Typer(
    help="Capability namespace — create and validate governed capability identifiers.",
    no_args_is_help=True,
)

passport_app = typer.Typer(
    help="Capability passport generation — generate and inspect governed passport artifacts.",
    no_args_is_help=True,
)

app.add_typer(runtime_app, name="runtime")
app.add_typer(init_app, name="init")
app.add_typer(context_app, name="context")
app.add_typer(runs_app, name="runs")
app.add_typer(repo_app, name="repo")
app.add_typer(dependency_app, name="dependency")
app.add_typer(explain_app, name="explain")
app.add_typer(capability_app, name="capability")
app.add_typer(passport_app, name="passport")


def _print_json(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2))


def _load_payload(payload_json: Optional[str], payload_file: Optional[Path]) -> dict[str, Any]:
    if payload_json and payload_file:
        raise typer.BadParameter("Use either --payload-json or --payload-file, not both.")

    if payload_json:
        try:
            value = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON passed to --payload-json: {exc}") from exc

        if not isinstance(value, dict):
            raise typer.BadParameter("--payload-json must decode to a JSON object.")

        return value

    if payload_file:
        try:
            value = json.loads(payload_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise typer.BadParameter(f"Payload file not found: {payload_file}") from exc
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON in payload file {payload_file}: {exc}") from exc

        if not isinstance(value, dict):
            raise typer.BadParameter("--payload-file must contain a JSON object.")

        return value

    return {}


def _handle_request_error(exc: Exception) -> None:
    typer.secho(f"Request failed: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-00: Identity Creation & Verification Commands
# ──────────────────────────────────────────────────────────────


@app.command()
def register(
    email: str = typer.Option(..., "--email", help="Builder email address."),
    username: str = typer.Option(..., "--username", help="Builder username."),
    display_name: str = typer.Option(..., "--display-name", help="Builder display name."),
    realm: str = typer.Option(
        "kh-dev",
        "--realm",
        help="Target realm: kh-prod, kh-dev, keyhole-mcp.",
    ),
    origin: str = typer.Option(
        "",
        "--origin",
        help="Origin classification (required for kh-dev). E.g.: smoke, test, integration.",
    ),
    purpose: str = typer.Option(
        "",
        "--purpose",
        help="Purpose classification (required for kh-dev). E.g.: sdk_onboarding, sdk_smoke.",
    ),
    tenant: str = typer.Option("", "--tenant", help="Tenant context."),
    org: str = typer.Option("", "--org", help="Organization context."),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Register a new builder identity through the governed boundary."""
    emit(
        run_register(
            email=email,
            username=username,
            display_name=display_name,
            realm=realm,
            origin=origin,
            purpose=purpose,
            tenant=tenant,
            org=org,
            mcp_url=mcp_url,
        ),
        use_json=use_json,
    )


@app.command()
def verify(
    registration_id: str = typer.Option(..., "--registration-id", help="Registration ID to verify."),
    code: str = typer.Option("", "--code", help="Verification code."),
    token: str = typer.Option("", "--token", help="Verification token."),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Complete verification for a pending registration."""
    emit(
        run_verify(
            registration_id=registration_id,
            code=code,
            token=token,
            mcp_url=mcp_url,
        ),
        use_json=use_json,
    )


@app.command(name="registration-status")
def registration_status(
    registration_id: str = typer.Option(..., "--registration-id", help="Registration ID to inspect."),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Inspect current onboarding state for a registration."""
    emit(
        run_registration_status(
            registration_id=registration_id,
            mcp_url=mcp_url,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-01: Authentication Bootstrap Commands
# ──────────────────────────────────────────────────────────────


@app.command()
def login(
    flow: str = typer.Option(
        "pkce",
        "--flow",
        help="Auth flow type: pkce (browser), device (headless), or password (ROPC/dev-only).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force re-authentication even if a valid session exists.",
    ),
    auth_server: str = typer.Option(
        "https://auth.keyholesolution.com/realms/keyhole-mcp",
        "--auth-server",
        envvar="KEYHOLE_AUTH_SERVER",
        help="Auth server URL.",
    ),
    client_id: str = typer.Option(
        "keyhole-cli",
        "--client-id",
        envvar="KEYHOLE_CLIENT_ID",
        help="OAuth2 client ID.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    username: Optional[str] = typer.Option(
        None,
        "--username",
        envvar="KEYHOLE_TEST_USERNAME",
        help="Username for password flow (dev/test only).",
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        envvar="KEYHOLE_TEST_PASSWORD",
        help="Password for password flow (dev/test only).",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Authenticate with the Keyhole boundary."""
    emit(
        run_login(
            flow=flow,
            force=force,
            auth_server_url=auth_server,
            client_id=client_id,
            mcp_base_url=mcp_url,
            username=username,
            password=password,
        ),
        use_json=use_json,
    )


@app.command()
def whoami(
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Inspect your authenticated identity context."""
    emit(run_whoami(mcp_base_url=mcp_url), use_json=use_json)


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-09: Governed Run Dispatch
# ──────────────────────────────────────────────────────────────


@app.command(name="run")
def cmd_run(
    run_type: str = typer.Option(
        "context.compile",
        "--run-type",
        help="Exact canonical run-type key.",
    ),
    shadow: bool = typer.Option(
        False,
        "--shadow",
        help="Execute in shadow (non-canonical) mode.",
    ),
    context: str = typer.Option(
        "",
        "--context",
        help="Context reference (path, digest, or 'auto').",
    ),
    input_file: str = typer.Option(
        "",
        "--input",
        help="Path to a JSON input file for the run.",
    ),
    output_path: str = typer.Option(
        "",
        "--output",
        help="Path to write run output.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Execute a governed run through the MCP boundary."""
    emit(
        run_run(
            run_type=run_type,
            shadow=shadow,
            context=context,
            input_file=input_file,
            output_path=output_path,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-10: Repository Ingestion and Graph
# ──────────────────────────────────────────────────────────────


@app.command(name="ingest")
def cmd_ingest(
    repo_path: str = typer.Argument(
        ".",
        help="Path to the repository to ingest.",
    ),
    shadow: bool = typer.Option(
        False,
        "--shadow",
        help="Execute in shadow (exploratory) mode.",
    ),
    include: Optional[list[str]] = typer.Option(
        None,
        "--include",
        help="Additional include glob patterns.",
    ),
    exclude: Optional[list[str]] = typer.Option(
        None,
        "--exclude",
        help="Additional exclude glob patterns.",
    ),
    max_bytes: int = typer.Option(
        0,
        "--max-bytes",
        help="Maximum total bytes to include (0 = unlimited).",
    ),
    summary_only: bool = typer.Option(
        False,
        "--summary-only",
        help="Scan and package only — do not submit.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Ingest an existing repository for graph analysis and alignment guidance."""
    emit(
        run_ingest(
            repo_path=repo_path,
            shadow=shadow,
            include=include,
            exclude=exclude,
            max_bytes=max_bytes,
            summary_only=summary_only,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-11: Alignment Guidance
# ──────────────────────────────────────────────────────────────


@app.command(name="align")
def cmd_align(
    repo_path: str = typer.Argument(
        ".",
        help="Path to the repository to align.",
    ),
    analysis_id: str = typer.Option(
        "",
        "--analysis-id",
        help="Analysis ID from a previous ingestion run.",
    ),
    from_ingestion: str = typer.Option(
        "",
        "--from-ingestion",
        help="Correlation ID from a previous ingestion to load saved artifacts.",
    ),
    shadow: bool = typer.Option(
        False,
        "--shadow",
        help="Execute in shadow (exploratory) mode.",
    ),
    local_only: bool = typer.Option(
        False,
        "--local-only",
        help="Render guidance from local artifacts only (no MCP call).",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Show alignment guidance for the current repository.

    Never mutates the repository. Guidance only.
    """
    emit(
        run_align(
            repo_path=repo_path,
            analysis_id=analysis_id,
            from_ingestion=from_ingestion,
            shadow=shadow,
            local_only=local_only,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# S41-02: First-Success Commands
# ──────────────────────────────────────────────────────────────


@app.command()
def doctor(
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
    mode: str = typer.Option(
        "local_only",
        "--mode",
        help="Operating mode: local_only or governed.",
    ),
    runtime_url: str = typer.Option(
        "",
        "--runtime-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Runtime URL for health checks (governed mode).",
    ),
    verify: bool = typer.Option(
        False,
        "--verify",
        help="Run verification-after-repair mode.",
    ),
    goal: str = typer.Option("", "--goal", help="Goal description for repair plan."),
) -> None:
    """Diagnose environment, compute repair plan, and verify."""
    emit(
        run_doctor(
            mode=mode,
            runtime_url=runtime_url,
            verify=verify,
            goal=goal,
        ),
        use_json=use_json,
    )


@init_app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    directory: str = typer.Option(".", "--dir", "-d", help="Directory to initialize."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Initialize a first-success workspace (default), or use a subcommand."""
    if ctx.invoked_subcommand is None:
        emit(run_init(directory=directory), use_json=use_json)


@init_app.command("vertical")
def init_vertical(
    name: str = typer.Argument(default="", help="Name for the new repo scaffold directory."),
    path: str = typer.Option("", "--path", "-p", help="Explicit target directory path."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing managed scaffold files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created without writing."),
    template: str = typer.Option("default", "--template", "-t", help="Scaffold template name."),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Disable interactive prompts."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Generate a canonical governed participant repo scaffold."""
    emit(
        run_init_vertical(
            name=name,
            path=path,
            force=force,
            dry_run=dry_run,
            template=template,
            non_interactive=non_interactive,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-16: Context Lifecycle Commands
# ──────────────────────────────────────────────────────────────


@context_app.command("compile")
def cmd_context_compile(
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    mode: str = typer.Option(
        "",
        "--mode",
        help="Compile mode.",
    ),
    origin: str = typer.Option(
        "",
        "--origin",
        help="Origin classification.",
    ),
    purpose: str = typer.Option(
        "",
        "--purpose",
        help="Purpose classification.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Compile governed context for the current repo and identity."""
    emit(
        run_context_compile(
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
            mode=mode,
            origin=origin,
            purpose=purpose,
        ),
        use_json=use_json,
    )


@context_app.command("inspect")
def cmd_context_inspect(
    digest: str = typer.Option(
        "",
        "--digest",
        help="The ctxpack_digest to inspect. Omit to use most recently compiled.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Inspect a governed context digest to understand its state-of-truth."""
    emit(
        run_context_inspect(
            digest=digest,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@app.command()
def smoke(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Run the canonical first-success verification."""
    emit(run_smoke(endpoint=base_url), use_json=use_json)


@runtime_app.command("start")
def cmd_runtime_start(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Start the local public test runtime."""
    emit(run_start(endpoint=base_url), use_json=use_json)


@runtime_app.command("stop")
def cmd_runtime_stop(
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Stop the local public test runtime."""
    emit(run_stop(), use_json=use_json)


@runtime_app.command("status")
def cmd_runtime_status(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Report truthful runtime state and public mode."""
    emit(run_status(endpoint=base_url), use_json=use_json)


# ──────────────────────────────────────────────────────────────
# Legacy / existing SDK-backed commands (preserved)
# ──────────────────────────────────────────────────────────────


@runtime_app.command("health")
def runtime_health(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
) -> None:
    """Check runtime health."""
    client = KeyholeClient(base_url=base_url)
    try:
        _print_json(client.health())
    except RequestException as exc:
        _handle_request_error(exc)
    finally:
        client.close()


@runtime_app.command("identity")
def runtime_identity(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
) -> None:
    """Return runtime identity and declared capabilities."""
    client = KeyholeClient(base_url=base_url)
    try:
        data = client.identity()
        _print_json(data)
    except RequestException as exc:
        _handle_request_error(exc)
    finally:
        client.close()


@runtime_app.command("state")
def runtime_state(
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
) -> None:
    """Return the current runtime-local state view."""
    client = KeyholeClient(base_url=base_url)
    try:
        _print_json(client.state())
    except RequestException as exc:
        _handle_request_error(exc)
    finally:
        client.close()


@runtime_app.command("realize")
def runtime_realize(
    candidate_digest: str = typer.Argument(
        ...,
        help="Candidate digest to submit to the runtime.",
    ),
    payload_json: Optional[str] = typer.Option(
        None,
        "--payload-json",
        help="Inline JSON object payload to include with the request.",
    ),
    payload_file: Optional[Path] = typer.Option(
        None,
        "--payload-file",
        exists=False,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to a JSON file containing the payload object.",
    ),
    base_url: str = typer.Option(
        DEFAULT_RUNTIME_URL,
        "--base-url",
        envvar="KEYHOLE_RUNTIME_URL",
        help="Base URL of the Keyhole runtime.",
    ),
) -> None:
    """Submit a bounded realization request."""
    payload = _load_payload(payload_json, payload_file)

    client = KeyholeClient(base_url=base_url)
    try:
        data = client.realize(candidate_digest=candidate_digest, payload=payload)
        _print_json(data)
    except RequestException as exc:
        _handle_request_error(exc)
    finally:
        client.close()


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-17: Async Run Lifecycle Commands
# ──────────────────────────────────────────────────────────────


@runs_app.command("status")
def cmd_runs_status(
    run_id: str = typer.Argument(..., help="The run ID or correlation ID to check."),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Check the current state of a governed run."""
    emit(
        run_runs_status(
            run_id=run_id,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@runs_app.command("wait")
def cmd_runs_wait(
    run_id: str = typer.Argument(..., help="The run ID to wait for."),
    poll_interval: float = typer.Option(
        3.0,
        "--poll-interval",
        help="Seconds between status polls.",
    ),
    max_polls: int = typer.Option(
        200,
        "--max-polls",
        help="Maximum number of polls before timeout.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Poll until a governed run reaches a terminal state."""
    emit(
        run_runs_wait(
            run_id=run_id,
            poll_interval=poll_interval,
            max_polls=max_polls,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@runs_app.command("tail")
def cmd_runs_tail(
    run_id: str = typer.Argument(..., help="The run ID to follow."),
    poll_interval: float = typer.Option(
        2.0,
        "--poll-interval",
        help="Seconds between observation polls.",
    ),
    max_entries: int = typer.Option(
        100,
        "--max-entries",
        help="Maximum observation entries to collect.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Follow run observations using the best available method (currently status polling)."""
    emit(
        run_runs_tail(
            run_id=run_id,
            poll_interval=poll_interval,
            max_entries=max_entries,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@runs_app.command("resume")
def cmd_runs_resume(
    identifier: str = typer.Argument(..., help="Run ID, request ID, or correlation ID to resume."),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Reconnect to an existing governed run identity."""
    emit(
        run_runs_resume(
            identifier=identifier,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@runs_app.command("list")
def cmd_runs_list(
    limit: int = typer.Option(
        10,
        "--limit",
        help="Maximum number of recent runs to list.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """List recent local run records."""
    emit(
        run_runs_list(
            limit=limit,
            repo_dir=repo_dir,
        ),
        use_json=use_json,
    )


@runs_app.command("budget")
def cmd_runs_budget(
    run_id: str = typer.Argument(..., help="Run ID to inspect budget and limit posture for."),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        help="Override proof state directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Show budget and limit posture for a run."""
    emit(
        run_budget(
            run_id=run_id,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
            state_dir=state_dir,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-20: Governance Explainability
# ──────────────────────────────────────────────────────────────


@explain_app.command("run")
def cmd_explain_run(
    run_id: str = typer.Argument(..., help="Run ID to explain."),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        help="Override proof state directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Explain a governed run — outcome, reason, evidence, and repair guidance."""
    emit(
        run_explain_run(
            run_id=run_id,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
            state_dir=state_dir,
        ),
        use_json=use_json,
    )


@app.command("inspect")
def cmd_inspect(
    request_id: str = typer.Argument(..., help="Request ID to inspect."),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        help="Override proof state directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Inspect a request — execution status, replay disposition, and context ref."""
    emit(
        run_inspect_request(
            request_id=request_id,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
            repo_dir=repo_dir,
            state_dir=state_dir,
        ),
        use_json=use_json,
    )


@app.command("support-bundle")
def cmd_support_bundle(
    identifier: str = typer.Argument(
        ...,
        help="Run ID or request ID for the support bundle.",
    ),
    run_id: str = typer.Option("", "--run-id", help="Explicit run ID (overrides identifier)."),
    request_id: str = typer.Option("", "--request-id", help="Explicit request ID (overrides identifier)."),
    repo_dir: str = typer.Option(
        ".",
        "--repo-dir",
        help="Path to the governed repo directory.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        help="Override proof state directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Assemble a portable support bundle for escalation and audit."""
    emit(
        run_support_bundle(
            run_id=run_id or identifier,
            request_id=request_id or identifier,
            repo_dir=repo_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
            state_dir=state_dir,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-07: Repository Registration
# ──────────────────────────────────────────────────────────────


@repo_app.command("register")
def cmd_repo_register(
    path: str = typer.Option(
        ".",
        "--path",
        help="Path to the repository to register.",
    ),
    shadow: bool = typer.Option(
        False,
        "--shadow",
        help="Shadow (observational) registration mode.",
    ),
    from_ingest: str = typer.Option(
        "",
        "--from-ingest",
        help="Register from a prior ingestion ID or correlation ID.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Disable interactive prompts.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Register a repository with the MCP boundary for governed participation."""
    emit(
        run_repo_register(
            repo_path=path,
            shadow=shadow,
            from_ingest=from_ingest,
            non_interactive=non_interactive,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-08: Capability Discovery and Resolution
# ──────────────────────────────────────────────────────────────


@app.command(name="search")
def cmd_search(
    query: str = typer.Argument(..., help="Capability name or namespace prefix to search for."),
    provider: str = typer.Option(
        "",
        "--provider",
        help="Filter by provider name.",
    ),
    version: str = typer.Option(
        "",
        "--version",
        help="Filter by version constraint.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Search the governed capability registry."""
    emit(
        run_search(
            query=query,
            provider=provider,
            version=version,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@dependency_app.command("resolve")
def cmd_dependency_resolve(
    capability: str = typer.Argument(..., help="Capability to resolve as a dependency."),
    provider: str = typer.Option(
        "",
        "--provider",
        help="Pin a specific provider.",
    ),
    version: str = typer.Option(
        "",
        "--version",
        help="Pin a specific version.",
    ),
    write: bool = typer.Option(
        False,
        "--write",
        help="Write the resolved dependency to dependencies.yaml (native repos only).",
    ),
    advisory: bool = typer.Option(
        False,
        "--advisory",
        help="Emit advisory artifact only (no repo mutation). This is the default.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        help="Path to the repository.",
    ),
    mcp_url: str = typer.Option(
        "https://mcp.keyholesolution.com",
        "--mcp-url",
        envvar="KEYHOLE_MCP_URL",
        help="MCP boundary base URL.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override credential store directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Resolve a capability to a deterministic dependency."""
    emit(
        run_dependency_resolve(
            capability=capability,
            provider=provider,
            version=version,
            write=write,
            advisory=advisory,
            repo_path=path,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-18: Memory Boundary Enforcement
# Registers a 'memory' command group that always rejects with repair guidance.
# No sub-commands (query, write, get, delete) are registered.
# Direct canonical memory access is not exposed by the public CLI.
# ──────────────────────────────────────────────────────────────

memory_app = typer.Typer(
    help=(
        "[REJECTED] Direct canonical memory access is not exposed by the public CLI.\n\n"
        "Use governed context, governed runs, or proof/explain surfaces instead:\n"
        "  keyhole context compile\n"
        "  keyhole context inspect\n"
        "  keyhole run --context <digest>"
    ),
    no_args_is_help=False,
    invoke_without_command=True,
)
app.add_typer(memory_app, name="memory")


@memory_app.callback(invoke_without_command=True)
def memory_boundary_reject(ctx: typer.Context) -> None:
    """[REJECTED] Direct canonical memory access is not exposed by the public CLI."""
    from keyhole_sdk.memory_boundary import MEMORY_BOUNDARY_REJECTION_MESSAGE

    typer.secho(
        MEMORY_BOUNDARY_REJECTION_MESSAGE,
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-03: Capability Namespace Commands
# ──────────────────────────────────────────────────────────────


@capability_app.command("create")
def cmd_capability_create(
    domain: str = typer.Option(..., "--domain", help="Top-level domain (e.g. payment)."),
    category: str = typer.Option(..., "--category", help="Category within domain (e.g. stripe)."),
    name: str = typer.Option(..., "--name", help="Capability name (e.g. integration)."),
    major: int = typer.Option(1, "--major", help="Major version number (positive integer)."),
    write: bool = typer.Option(False, "--write/--no-write", help="Write to governed artifact when in a native repo."),
    repo_dir: str = typer.Option(".", "--repo-dir", help="Target repository directory."),
    state_dir: str = typer.Option("", "--state-dir", envvar="KEYHOLE_STATE_DIR", help="Tool-owned state directory for proof artifacts."),
    mcp_url: str = typer.Option("https://mcp.keyholesolution.com", "--mcp-url", envvar="KEYHOLE_MCP_URL", help="MCP boundary base URL."),
    keyhole_home: str = typer.Option("", "--keyhole-home", envvar="KEYHOLE_HOME", help="Keyhole home directory."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Create a canonical capability name from structured parts.

    Validates parts, normalises obvious input issues, assembles the canonical
    name, and optionally writes to a governed local artifact.

    Example:
      keyhole capability create --domain payment --category stripe --name integration --major 1
    """
    emit(
        run_capability_create(
            domain=domain,
            category=category,
            name=name,
            major=major,
            repo_dir=repo_dir,
            write=write,
            state_dir=state_dir,
            mcp_url=mcp_url,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@capability_app.command("validate")
def cmd_capability_validate(
    capability_name: str = typer.Argument(..., help="Capability name to validate (e.g. payment.stripe.integration.v1)."),
    repo_dir: str = typer.Option(".", "--repo-dir", help="Target repository directory."),
    state_dir: str = typer.Option("", "--state-dir", envvar="KEYHOLE_STATE_DIR", help="Tool-owned state directory for proof artifacts."),
    keyhole_home: str = typer.Option("", "--keyhole-home", envvar="KEYHOLE_HOME", help="Keyhole home directory."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Validate a capability name against the canonical namespace contract.

    Accepts ``<domain>.<category>.<capability>.v<major>`` format.
    Advisory only — never mutates the repo.

    Example:
      keyhole capability validate payment.stripe.integration.v1
    """
    emit(
        run_capability_validate(
            capability_name=capability_name,
            repo_dir=repo_dir,
            state_dir=state_dir,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ──────────────────────────────────────────────────────────────
# SDK-CLIENT-04: Governance Contract Validation
# ──────────────────────────────────────────────────────────────


@app.command("validate")
def cmd_validate(
    repo_dir: str = typer.Argument(
        ".",
        help="Repository directory to validate (default: current directory).",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Validation mode: auto (detect posture), native (strict), advisory (always advisory).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Strict mode: elevate warnings to failures and run additional checks.",
    ),
    proof: bool = typer.Option(
        False,
        "--proof",
        help="Force local validation proof artifact emission even without --state-dir.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress non-error output (next_steps, summary) on success.",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        envvar="KEYHOLE_STATE_DIR",
        help="Tool-owned state directory for proof artifacts.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override Keyhole home directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Validate local governance contract and dependency schema.

    Reads keyhole.yaml, governance_contract.yaml, capability_passport.yaml,
    and dependencies.yaml if present.  Advisory-only for non-native repos.

    Exits 0 on PASS or WARN.  Exits 5 on REJECT.
    Never requires MCP connectivity.

    Examples:
      keyhole validate
      keyhole validate ./my-service
      keyhole validate --mode native
      keyhole validate --strict
      keyhole validate --proof --state-dir /tmp/kh-state
      keyhole validate --quiet --json
    """
    emit(
        run_validate(
            repo_path=repo_dir,
            mode=mode,
            strict=strict,
            proof=proof,
            quiet=quiet,
            state_dir=state_dir,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


# ── keyhole passport ─────────────────────────────────────────────────────────


@passport_app.command("generate")
def cmd_passport_generate(
    repo_dir: str = typer.Argument(".", help="Repository directory to generate passport for."),
    write: bool = typer.Option(
        True,
        "--write/--no-write",
        help="Write capability_passport.yaml into the repo (default: write).",
    ),
    output: str = typer.Option(
        "",
        "--output",
        help="Override write path (absolute or relative).",
    ),
    state_dir: str = typer.Option(
        "",
        "--state-dir",
        envvar="KEYHOLE_STATE_DIR",
        help="Tool state directory for proof emission.",
    ),
    keyhole_home: str = typer.Option(
        "",
        "--keyhole-home",
        envvar="KEYHOLE_HOME",
        help="Override Keyhole home directory.",
    ),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Generate a capability passport from declared local repo truth.

    Only works for native governed repos with valid declared capabilities.
    Foreign repos and repos without declared capabilities are rejected.
    Never requires MCP connectivity.

    Examples:
      keyhole passport generate
      keyhole passport generate ./my-service
      keyhole passport generate --no-write --json
    """
    emit(
        run_passport_generate(
            repo_path=repo_dir,
            write=write,
            output=output,
            state_dir=state_dir,
            keyhole_home=keyhole_home,
        ),
        use_json=use_json,
    )


@passport_app.command("show")
def cmd_passport_show(
    repo_dir: str = typer.Argument(".", help="Repository directory to read passport from."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Display the capability passport from the repo.

    Read-only.  Never generates or mutates.

    Examples:
      keyhole passport show
      keyhole passport show ./my-service --json
    """
    emit(
        run_passport_show(repo_path=repo_dir),
        use_json=use_json,
    )