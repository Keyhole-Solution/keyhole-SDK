from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"
APP_ROOT = REPO_ROOT / "my-first-app"
TEST_DIR = Path(__file__).resolve().parent

for path in (SDK_ROOT, TEST_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from keyhole_sdk.governed_demo import GovernedDemoError, GovernedFirstAppClient
from s51_c02_fakes import FakeBoundarySession


def test_sdk_discovers_capabilities_and_required_operations() -> None:
    session = FakeBoundarySession()
    client = GovernedFirstAppClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=session,
    )

    operations = client.discover()

    assert "repo.register" in operations
    assert "context.compile" in operations


def test_sdk_repo_registration_calls_boundary_and_stores_identity(tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    client = GovernedFirstAppClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=session,
    )

    result = client.register_repo(app)

    assert result["registration_id"] == "reg_fake_123"
    assert (app / ".keyhole" / "governed-demo" / "registration.json").exists()
    assert any(call["url"].endswith("/mcp/v1/repos/register") for call in session.calls)


def test_sdk_context_compile_returns_governance_context_id(tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    client = GovernedFirstAppClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=session,
    )
    client.register_repo(app)

    result = client.compile_context(app)

    assert result["governance_context_id"] == "gctx_fake_123"
    assert (app / ".keyhole" / "governed-demo" / "context.json").exists()
    assert any(call["url"].endswith("/mcp/v1/runs/start") for call in session.calls)


def test_sdk_governed_realization_sends_require_governed_and_returns_receipt(tmp_path) -> None:
    app = _copy_first_app(tmp_path)
    session = FakeBoundarySession()
    client = GovernedFirstAppClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=session,
    )
    client.register_repo(app)
    client.compile_context(app)

    receipt = client.run_governed_realization(app)

    realize_call = [call for call in session.calls if call["url"].endswith("/realize")][0]
    assert realize_call["json"]["require_governed"] is True
    assert realize_call["json"]["local_invariant_result"]["verdict"] == "ACCEPT"
    assert receipt.governed is True
    assert receipt.event_spine_evidence is True
    assert receipt.governance_verdict == "ACCEPT"
    assert receipt.drift_state == "clean"


def test_missing_required_mcp_operation_fails_closed() -> None:
    client = GovernedFirstAppClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=FakeBoundarySession(missing_operation="context.compile"),
    )

    with pytest.raises(GovernedDemoError, match="context.compile"):
        client.discover()


def test_missing_token_fails_closed() -> None:
    with pytest.raises(GovernedDemoError, match="KEYHOLE_MCP_TOKEN"):
        GovernedFirstAppClient(mcp_url="https://mcp.fake", token="")


def _copy_first_app(tmp_path: Path) -> Path:
    target = tmp_path / "my-first-app"
    import shutil

    shutil.copytree(APP_ROOT, target, ignore=shutil.ignore_patterns(".keyhole", "proof_bundle"))
    return target
