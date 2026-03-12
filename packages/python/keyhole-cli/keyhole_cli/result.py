"""Shared result model and output rendering for keyhole-cli.

Every CLI command produces a ``CommandResult``, which is the single
truth source for both human and JSON rendering.  Exit codes are
derived deterministically from the result.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import typer


# ──────────────────────────────────────────────────────────────
# Exit codes — deterministic and documented
# ──────────────────────────────────────────────────────────────
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_UNSUPPORTED = 2
EXIT_RUNTIME_UNAVAILABLE = 3
EXIT_INVALID_INPUT = 4
EXIT_CONTRACT_FAILURE = 5


class CommandResult:
    """Structured result produced by every CLI command.

    Both ``render_human`` and ``render_json`` read from the same data,
    so outputs are always semantically equivalent.
    """

    def __init__(
        self,
        command: str,
        success: bool,
        *,
        exit_code: int = EXIT_SUCCESS,
        data: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        summary: Optional[str] = None,
    ) -> None:
        self.command = command
        self.success = success
        self.exit_code = exit_code
        self.data: Dict[str, Any] = data or {}
        self.warnings: List[str] = warnings or []
        self.next_steps: List[str] = next_steps or []
        self.summary = summary
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Full machine-readable dict for JSON output."""
        base: Dict[str, Any] = {
            "command": self.command,
            "success": self.success,
        }
        base.update(self.data)
        if self.warnings:
            base["warnings"] = self.warnings
        if self.next_steps:
            base["next_steps"] = self.next_steps
        if self.summary:
            base["summary"] = self.summary
        base["timestamp"] = self.timestamp
        return base


def emit(result: CommandResult, *, use_json: bool) -> None:
    """Render a ``CommandResult`` to the terminal.

    When *use_json* is ``True``, output is pure JSON (no ANSI).
    Otherwise, human-friendly text is written to stdout.
    """
    if use_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _render_human(result)
    raise typer.Exit(code=result.exit_code)


def _render_human(result: CommandResult) -> None:
    """Write a concise human-readable summary to stdout."""
    ok = "✓" if result.success else "✗"
    color = typer.colors.GREEN if result.success else typer.colors.RED
    typer.secho(f"{ok} {result.command}", fg=color, bold=True)

    if result.summary:
        typer.echo(f"  {result.summary}")

    for key, value in result.data.items():
        if isinstance(value, (dict, list)):
            continue  # skip complex sub-structures in human view
        typer.echo(f"  {key}: {value}")

    if result.warnings:
        typer.secho("  Warnings:", fg=typer.colors.YELLOW)
        for w in result.warnings:
            typer.echo(f"    - {w}")

    if result.next_steps:
        typer.echo("  Next steps:")
        for s in result.next_steps:
            typer.echo(f"    → {s}")
