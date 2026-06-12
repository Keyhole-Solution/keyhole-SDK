from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import keyhole_sdk
from keyhole_cli.cli import app
from keyhole_sdk import KeyholeConfig


ROOT = Path(__file__).resolve().parents[1]


def test_public_sdk_top_level_surface_is_client_side() -> None:
    assert keyhole_sdk.KeyholeClient
    assert keyhole_sdk.GovernanceReceipt
    assert keyhole_sdk.run_validation
    assert "GovernanceProofRunner" not in keyhole_sdk.__all__
    assert "MEMORY_BOUNDARY_REJECTION_MESSAGE" not in keyhole_sdk.__all__


def test_default_config_has_no_private_server() -> None:
    config = KeyholeConfig()
    assert config.base_url == ""


def test_public_cli_surface_is_intentional() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    output = result.output
    for expected in ["doctor", "validate", "repo", "context", "run", "governed"]:
        assert expected in output
    for hidden in ["mcp-proxy", "workspace", "memory", "connections"]:
        assert hidden not in output


def test_no_live_governed_flow_is_available() -> None:
    result = CliRunner().invoke(
        app,
        ["governed", "run", "--repo-dir", str(ROOT / "my-first-app"), "--no-live", "--json"],
    )
    assert result.exit_code == 0
    assert "would_mutate_mcp" in result.output
