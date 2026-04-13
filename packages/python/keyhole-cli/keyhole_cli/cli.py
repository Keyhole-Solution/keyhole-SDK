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
from keyhole_cli.commands.run_cmd import run_run
from keyhole_cli.commands.runs_cmd import (
    run_runs_list,
    run_runs_resume,
    run_runs_status,
    run_runs_tail,
    run_runs_wait,
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

app.add_typer(runtime_app, name="runtime")
app.add_typer(init_app, name="init")
app.add_typer(context_app, name="context")
app.add_typer(runs_app, name="runs")


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


if __name__ == "__main__":
    app()