from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "services" / "test-runtime"


def _load_runtime(monkeypatch, *, mcp_url: str = "", token: str = ""):
    monkeypatch.setenv("KEYHOLE_MCP_URL", mcp_url)
    monkeypatch.setenv("KEYHOLE_MCP_TOKEN", token)
    if str(RUNTIME_ROOT) not in sys.path:
        sys.path.insert(0, str(RUNTIME_ROOT))
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)
    return importlib.import_module("app.bridge"), importlib.import_module("app.state")


def test_runtime_local_only_realization_receipt_is_not_governed(monkeypatch) -> None:
    bridge, state_module = _load_runtime(monkeypatch)
    verdict = asyncio.run(bridge.governance_check("sha256:local", {}))

    receipt = state_module.RuntimeState().apply_digest(
        "sha256:local",
        governance_verdict=verdict["verdict"],
    )

    assert receipt["governed"] is False
    assert receipt["event_spine_evidence"] is False
    assert receipt["governance_verdict"] == "LOCAL_ONLY"


def test_runtime_require_governed_without_mcp_has_fail_closed_route() -> None:
    routes = (RUNTIME_ROOT / "app" / "routes.py").read_text()

    assert "request.require_governed" in routes
    assert "status_code=412" in routes
    assert '"governed": False' in routes
    assert '"event_spine_evidence": False' in routes


def test_runtime_governed_realization_preserves_verdict_and_drift(monkeypatch) -> None:
    bridge, state_module = _load_runtime(
        monkeypatch,
        mcp_url="https://mcp.fake",
        token="secret-token",
    )

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {
                "ok": True,
                "run_id": "run_fake_123",
                "result": {
                    "governance_verdict": "ACCEPT",
                    "drift_state": "clean",
                    "governance_context_id": "gctx_fake_123",
                    "mcp_event_id": "evt_fake_123",
                },
            }

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, *args: Any, **kwargs: Any) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(bridge.httpx, "AsyncClient", FakeAsyncClient)
    verdict = asyncio.run(bridge.governance_check("sha256:governed", {}))
    evidence = verdict["governance_receipt"]

    runtime_state = state_module.RuntimeState()
    receipt = runtime_state.apply_digest(
        "sha256:governed",
        governance_verdict=evidence["governance_verdict"],
        governed=evidence["governed"],
        event_spine_evidence=evidence["event_spine_evidence"],
        governance_context_id=evidence["governance_context_id"],
        drift_state=evidence["drift_state"],
        mcp_event_id=evidence["mcp_event_id"],
    )

    assert receipt["governance_verdict"] == "ACCEPT"
    assert receipt["drift_state"] == "clean"
    assert runtime_state.get_state()["governance_receipts"][0]["mcp_event_id"] == "evt_fake_123"


def test_runtime_missing_upstream_evidence_has_fail_closed_route() -> None:
    routes = (RUNTIME_ROOT / "app" / "routes.py").read_text()

    assert "status_code=502" in routes
    assert "upstream evidence fields" in routes
    assert "event_spine_evidence" in routes
