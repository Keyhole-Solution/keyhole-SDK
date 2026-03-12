from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from requests import RequestException

from keyhole_sdk import KeyholeClient

from keyhole_cli.result import emit
from keyhole_cli.commands.doctor import run_doctor
from keyhole_cli.commands.init_cmd import run_init
from keyhole_cli.commands.runtime import run_start, run_stop, run_status
from keyhole_cli.commands.smoke import run_smoke

DEFAULT_RUNTIME_URL = "http://localhost:8080"

app = typer.Typer(
    help="Command-line interface for the Keyhole Developer Kit.",
    no_args_is_help=True,
)

runtime_app = typer.Typer(
    help="Interact with a Keyhole-compatible runtime.",
    no_args_is_help=True,
)

app.add_typer(runtime_app, name="runtime")


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


@app.command()
def init(
    directory: str = typer.Option(".", "--dir", "-d", help="Directory to initialize."),
    use_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output."),
) -> None:
    """Initialize a first-success workspace."""
    emit(run_init(directory=directory), use_json=use_json)


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


if __name__ == "__main__":
    app()