from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"
CLI_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-cli"
TEST_DIR = Path(__file__).resolve().parent
SECOND_APP_ROOT = REPO_ROOT / "examples" / "second-governed-app"

for path in (SDK_ROOT, CLI_ROOT, TEST_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import keyhole_sdk.governed_demo as governed_demo
import keyhole_sdk.governed_flow as governed_flow
import keyhole_cli.commands.governed_flow_cmd as governed_flow_cmd
from keyhole_sdk.governed_demo import GovernedDemoError
from keyhole_sdk.governed_flow import GovernedRepoFlowClient, GovernedRunStateStore
from s51_c02_fakes import FakeBoundarySession


def test_governed_run_persists_local_state_after_gap_resolution(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = _client(_second_session(capability_shape="storyless_gap"))

    result = client.run_governed_repo_flow(app, dry_run=True)
    state = _latest_state(app)

    assert result["resolved_gap_id"] == "gap_fake_c03_456"
    assert state["resolved_gap_id"] == "gap_fake_c03_456"
    assert state["gap_id_source"] == "gaps.list"


def test_governed_run_persists_local_state_after_claim(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = _client(FakeBoundarySession(capability_shape="live_envelope"))

    client.inspect_repo(app)
    client.discover()
    claim = client.claim_gap(app)
    client._persist_state({
        "resolved_gap_id": claim["gap_id"],
        "gap_id_source": claim["gap_id_source"],
        "claim_id": claim["claim_id"],
        "claim_ref": claim["claim_ref"],
        "status": "claim_succeeded",
        "step": "claim_succeeded",
    })
    state = _latest_state(app)

    assert state["claim_id"] == "claim_fake_123"
    assert state["claim_ref"] == "claim_ref_fake_123"


def test_governed_run_persists_local_state_after_context_creation(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = _client(FakeBoundarySession(capability_shape="live_envelope"))

    client.inspect_repo(app)
    client.discover()
    claim = client.claim_gap(app)
    client._persist_state({
        "resolved_gap_id": claim["gap_id"],
        "gap_id_source": claim["gap_id_source"],
        "claim_id": claim["claim_id"],
        "claim_ref": claim["claim_ref"],
    })
    registration = client.register_repo(app)
    client._persist_state({"registration_id": registration["registration_id"], "status": "context_created"})
    state = _latest_state(app)

    assert state["registration_id"] == "reg_fake_123"


def test_governed_run_persists_final_receipt(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = _client(FakeBoundarySession(capability_shape="live_envelope"))

    result = client.run_governed_repo_flow(app)
    state = _latest_state(app)

    assert result["receipt"]["receipt_id"] == "receipt_fake_123"
    assert state["receipt_id"] == "receipt_fake_123"
    assert state["proof_id"] == "proof_fake_123"
    assert state["terminal"] is True


def test_status_last_reads_local_state_and_polls_mcp(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    state = {
        "repo_dir": str(app),
        "repo_name": "second-governed-app",
        "repo_remote": "https://example.test/second-governed-app.git",
        "commit_sha": "def456abc123",
        "branch": "feature/c03",
        "repo_class": "SDK_TEMPLATE",
        "story_id": "CE-V5-S51-C03",
        "capability_id": "second-governed-app.echo.user.v1",
        "resolved_gap_id": "gap_fake_c03_456",
        "run_id": "run_fake_claim_123",
        "poll_url": "/mcp/v1/runs/run_fake_claim_123",
        "step": "gap_claim",
        "status": "accepted",
        "terminal": False,
    }
    GovernedRunStateStore(app).write(state)
    session = FakeBoundarySession(capability_shape="async_claim")
    monkeypatch.setattr(
        governed_flow_cmd,
        "_client",
        lambda **kwargs: GovernedRepoFlowClient(
            mcp_url="https://mcp.fake",
            token="secret-token",
            runtime_url="http://runtime.fake",
            session=session,
        ),
    )

    result = governed_flow_cmd.run_governed_status(repo_dir=str(app), mcp_url="https://mcp.fake")
    payload = result.to_dict()

    assert result.success is True
    assert payload["claim_id"] == "claim_fake_123"
    assert any("/mcp/v1/runs/run_fake_claim_123" in call["url"] for call in session.calls)


def test_resume_last_continues_from_claim_step_without_duplicate_claim(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    GovernedRunStateStore(app).write({
        "repo_dir": str(app),
        "repo_name": "second-governed-app",
        "repo_remote": "https://example.test/second-governed-app.git",
        "commit_sha": "def456abc123",
        "branch": "feature/c03",
        "repo_class": "SDK_TEMPLATE",
        "story_id": "CE-V5-S51-C03",
        "capability_id": "second-governed-app.echo.user.v1",
        "resolved_gap_id": "gap_fake_c03_456",
        "gap_id_source": "gaps.list",
        "claim_id": "claim_fake_123",
        "claim_ref": "claim_ref_fake_123",
        "status": "claim_succeeded",
        "step": "claim_succeeded",
        "terminal": False,
    })
    session = FakeBoundarySession(capability_shape="live_envelope")

    result = _client(session).resume_governed_repo_flow(app)

    run_types = [call["json"]["run_type"] for call in session.calls if call["url"].endswith("/mcp/v1/runs/start")]
    assert result["receipt"]["receipt_id"] == "receipt_fake_123"
    assert run_types.count("gaps.claim") == 0


def test_resume_last_continues_from_context_step(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    GovernedRunStateStore(app).write({
        "repo_dir": str(app),
        "repo_name": "second-governed-app",
        "repo_remote": "https://example.test/second-governed-app.git",
        "commit_sha": "def456abc123",
        "branch": "feature/c03",
        "repo_class": "SDK_TEMPLATE",
        "story_id": "CE-V5-S51-C03",
        "capability_id": "second-governed-app.echo.user.v1",
        "resolved_gap_id": "gap_fake_c03_456",
        "gap_id_source": "gaps.list",
        "claim_id": "claim_fake_123",
        "claim_ref": "claim_ref_fake_123",
        "registration_id": "reg_fake_123",
        "status": "context_created",
        "step": "context_created",
        "terminal": False,
    })
    session = FakeBoundarySession(capability_shape="live_envelope")

    result = _client(session).resume_governed_repo_flow(app)

    run_types = [call["json"]["run_type"] for call in session.calls if call["url"].endswith("/mcp/v1/runs/start")]
    assert result["receipt"]["receipt_id"] == "receipt_fake_123"
    assert "context.compile" in run_types
    assert "governed.realize" in run_types


def test_resume_last_continues_from_realization_step(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    GovernedRunStateStore(app).write({
        "repo_dir": str(app),
        "repo_name": "second-governed-app",
        "repo_remote": "https://example.test/second-governed-app.git",
        "commit_sha": "def456abc123",
        "branch": "feature/c03",
        "repo_class": "SDK_TEMPLATE",
        "story_id": "CE-V5-S51-C03",
        "capability_id": "second-governed-app.echo.user.v1",
        "resolved_gap_id": "gap_fake_c03_456",
        "gap_id_source": "gaps.list",
        "claim_id": "claim_fake_123",
        "claim_ref": "claim_ref_fake_123",
        "registration_id": "reg_fake_123",
        "governance_context_id": "gctx_fake_123",
        "status": "context_compiled",
        "step": "context_compiled",
        "terminal": False,
    })
    session = FakeBoundarySession(capability_shape="live_envelope")

    result = _client(session).resume_governed_repo_flow(app)

    run_types = [call["json"]["run_type"] for call in session.calls if call["url"].endswith("/mcp/v1/runs/start")]
    assert result["receipt"]["receipt_id"] == "receipt_fake_123"
    assert run_types == ["governed.realize"]


def test_receipt_last_prints_final_receipt(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = _client(FakeBoundarySession(capability_shape="live_envelope"))
    client.run_governed_repo_flow(app)
    monkeypatch.setattr(
        governed_flow_cmd,
        "_client",
        lambda **kwargs: GovernedRepoFlowClient(
            mcp_url="https://mcp.fake",
            token="secret-token",
            runtime_url="http://runtime.fake",
            session=FakeBoundarySession(capability_shape="live_envelope"),
        ),
    )

    result = governed_flow_cmd.run_governed_receipt(repo_dir=str(app), mcp_url="https://mcp.fake")
    payload = result.to_dict()

    assert result.success is True
    assert payload["receipt"]["receipt_id"] == "receipt_fake_123"
    assert payload["live_confirmed"] is True


def test_missing_local_state_fails_with_actionable_error(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    monkeypatch.setattr(
        governed_flow_cmd,
        "_client",
        lambda **kwargs: GovernedRepoFlowClient(
            mcp_url="https://mcp.fake",
            token="secret-token",
            runtime_url="http://runtime.fake",
            session=FakeBoundarySession(capability_shape="live_envelope"),
        ),
    )

    result = governed_flow_cmd.run_governed_status(repo_dir=str(app), mcp_url="https://mcp.fake")

    assert result.success is False
    assert "missing governed run state" in result.summary


def test_token_is_never_written_to_local_state(monkeypatch, tmp_path) -> None:
    app = _copy_second_app(tmp_path)
    _patch_git_metadata(monkeypatch)
    client = GovernedRepoFlowClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=FakeBoundarySession(capability_shape="live_envelope"),
    )

    client.run_governed_repo_flow(app)
    body = (app / ".keyhole" / "governed-runs" / "latest.json").read_text(encoding="utf-8").lower()

    assert "secret-token" not in body
    assert "authorization" not in body


def _copy_second_app(tmp_path: Path) -> Path:
    target = tmp_path / "second-governed-app"
    shutil.copytree(SECOND_APP_ROOT, target, ignore=shutil.ignore_patterns(".keyhole"))
    return target


def _latest_state(app: Path) -> dict[str, object]:
    return json.loads((app / ".keyhole" / "governed-runs" / "latest.json").read_text(encoding="utf-8"))


def _patch_git_metadata(monkeypatch) -> None:
    values = {
        ("remote", "get-url", "origin"): "https://example.test/second-governed-app.git",
        ("rev-parse", "HEAD"): "def456abc123",
        ("branch", "--show-current"): "feature/c03",
    }
    monkeypatch.setattr(governed_demo, "_git_value", lambda _repo, *args: values.get(tuple(args), ""))
    monkeypatch.setattr(governed_flow, "_repo_git_metadata", lambda repo: {
        "repo_remote": values[("remote", "get-url", "origin")],
        "commit_sha": values[("rev-parse", "HEAD")],
        "branch": values[("branch", "--show-current")],
    })


def _client(session: FakeBoundarySession) -> GovernedRepoFlowClient:
    return GovernedRepoFlowClient(
        mcp_url="https://mcp.fake",
        token="secret-token",
        runtime_url="http://runtime.fake",
        session=session,
    )


def _second_session(capability_shape: str = "live_envelope") -> FakeBoundarySession:
    return FakeBoundarySession(
        capability_shape=capability_shape,
        gap_id="gap_fake_c03_456",
        story_id="CE-V5-S51-C03",
        repo_name="second-governed-app",
        capability_id="second-governed-app.echo.user.v1",
    )
