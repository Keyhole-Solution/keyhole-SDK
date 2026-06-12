from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"
CLI_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-cli"
APP_ROOT = REPO_ROOT / "my-first-app"
TEST_DIR = Path(__file__).resolve().parent

for path in (SDK_ROOT, CLI_ROOT, TEST_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from keyhole_cli.commands import governed_demo_cmd
from s51_c02_fakes import FakeBoundarySession


def test_cli_repo_register_json_path_works_against_fake_mcp(monkeypatch, tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    _patch_session(monkeypatch, session)
    monkeypatch.setenv("KEYHOLE_MCP_TOKEN", "secret-token")

    result = governed_demo_cmd.run_governed_demo_register(
        repo_path=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    assert result.success is True
    payload = result.to_dict()
    assert payload["registration_id"] == "reg_fake_123"
    assert "secret-token" not in json.dumps(payload)


def test_cli_uses_device_login_credential_when_env_token_absent(monkeypatch, tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    _patch_session(monkeypatch, session)
    monkeypatch.delenv("KEYHOLE_MCP_TOKEN", raising=False)
    monkeypatch.setattr(governed_demo_cmd, "get_fresh_token", lambda: "device-login-token")

    result = governed_demo_cmd.run_governed_demo_register(
        repo_path=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    assert result.success is True
    assert result.to_dict()["registration_id"] == "reg_fake_123"
    assert "device-login-token" not in json.dumps(result.to_dict())


def test_cli_context_compile_json_works_against_fake_mcp(monkeypatch, tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    _patch_session(monkeypatch, session)
    monkeypatch.setenv("KEYHOLE_MCP_TOKEN", "secret-token")
    governed_demo_cmd.run_governed_demo_register(
        repo_path=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    result = governed_demo_cmd.run_governed_demo_context_compile(
        repo_dir=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    assert result.success is True
    payload = result.to_dict()
    assert payload["governance_context_id"] == "gctx_fake_123"
    assert "secret-token" not in json.dumps(payload)


def test_cli_run_context_auto_json_returns_governed_receipt(monkeypatch, tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    _patch_session(monkeypatch, session)
    monkeypatch.setenv("KEYHOLE_MCP_TOKEN", "secret-token")
    governed_demo_cmd.run_governed_demo_register(
        repo_path=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )
    governed_demo_cmd.run_governed_demo_context_compile(
        repo_dir=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    result = governed_demo_cmd.run_governed_demo_run(
        repo_dir=str(app),
        mcp_url="https://mcp.fake",
        runtime_url="http://runtime.fake",
    )

    payload = result.to_dict()
    assert result.success is True
    assert payload["governed"] is True
    assert payload["event_spine_evidence"] is True
    assert payload["governance_verdict"] == "ACCEPT"
    assert "secret-token" not in json.dumps(payload)


def _patch_session(monkeypatch, session: FakeBoundarySession) -> None:
    import keyhole_sdk.governed_demo as governed_demo

    monkeypatch.setattr(governed_demo.requests, "Session", lambda: session)


def _copy_first_app(tmp_path: Path) -> Path:
    target = tmp_path / "my-first-app"
    import shutil

    shutil.copytree(APP_ROOT, target, ignore=shutil.ignore_patterns(".keyhole", "proof_bundle"))
    return target
