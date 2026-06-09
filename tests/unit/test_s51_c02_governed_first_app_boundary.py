"""CE-V5-S51-C02 - governed first-app boundary connection."""
from __future__ import annotations

import importlib
import asyncio
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "services" / "test-runtime"
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"


def _load_runtime_modules(monkeypatch, *, mcp_url: str = "", mcp_token: str = ""):
    monkeypatch.setenv("KEYHOLE_MCP_URL", mcp_url)
    monkeypatch.setenv("KEYHOLE_MCP_TOKEN", mcp_token)
    if str(RUNTIME_ROOT) not in sys.path:
        sys.path.insert(0, str(RUNTIME_ROOT))
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)
    bridge = importlib.import_module("app.bridge")
    state = importlib.import_module("app.state")
    return bridge, state


def test_local_only_realize_reports_not_governed(monkeypatch) -> None:
    bridge, state_module = _load_runtime_modules(monkeypatch)

    verdict = asyncio.run(
        bridge.governance_check("sha256:local", {"local_invariant_result": {}})
    )
    receipt = state_module.RuntimeState().apply_digest(
        "sha256:local",
        governance_verdict=verdict["verdict"],
        governed=False,
        event_spine_evidence=False,
    )

    assert receipt["status"] == "ACCEPT"
    assert receipt["governed"] is False
    assert receipt["event_spine_evidence"] is False
    assert receipt["governance_verdict"] == "LOCAL_ONLY"
    assert receipt["drift_state"] == "not_applicable"


def test_require_governed_refuses_without_mcp(monkeypatch) -> None:
    routes = (RUNTIME_ROOT / "app" / "routes.py").read_text()

    assert "request.require_governed" in routes
    assert "status_code=412" in routes
    assert '"governed": False' in routes
    assert '"event_spine_evidence": False' in routes
    assert "KEYHOLE_MCP_URL" in routes


def test_governed_mode_calls_mcp_and_preserves_receipt(monkeypatch) -> None:
    bridge, state_module = _load_runtime_modules(
        monkeypatch,
        mcp_url="https://mcp.example.test",
        mcp_token="token",
    )

    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {
                "ok": True,
                "run_id": "run_123",
                "result": {
                    "governance_verdict": "ACCEPT",
                    "drift_state": "clean",
                    "governance_context_id": "gctx_123",
                    "mcp_event_id": "evt_123",
                    "proof_id": "proof_123",
                    "receipt_id": "receipt_123",
                },
            }

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(bridge.httpx, "AsyncClient", FakeAsyncClient)

    local_invariant = {
        "invariant_id": "MY-FIRST-APP-INV-01",
        "verdict": "ACCEPT",
    }
    verdict = asyncio.run(
        bridge.governance_check(
            "sha256:governed",
            {
            "governance_context_id": "gctx_123",
            "local_invariant_result": local_invariant,
            "passport_digest": "sha256:passport",
            "trust_digest": "sha256:trust",
            },
        )
    )

    governance_receipt = verdict["governance_receipt"]
    runtime_state = state_module.RuntimeState()
    receipt = runtime_state.apply_digest(
        "sha256:governed",
        governance_verdict=governance_receipt["governance_verdict"],
        governed=governance_receipt["governed"],
        event_spine_evidence=governance_receipt["event_spine_evidence"],
        governance_context_id=governance_receipt["governance_context_id"],
        drift_state=governance_receipt["drift_state"],
        mcp_event_id=governance_receipt["mcp_event_id"],
        proof_id=governance_receipt["proof_id"],
        receipt_id=governance_receipt["receipt_id"],
        passport_digest="sha256:passport",
        trust_digest="sha256:trust",
    )

    assert receipt["governed"] is True
    assert receipt["event_spine_evidence"] is True
    assert receipt["governance_verdict"] == "ACCEPT"
    assert receipt["drift_state"] == "clean"
    assert receipt["governance_context_id"] == "gctx_123"
    assert receipt["mcp_event_id"] == "evt_123"
    assert receipt["proof_id"] == "proof_123"
    assert receipt["receipt_id"] == "receipt_123"
    assert receipt["passport_digest"] == "sha256:passport"
    assert receipt["trust_digest"] == "sha256:trust"
    assert captured["json"]["parameters"]["payload"]["local_invariant_result"] == local_invariant

    state = runtime_state.get_state()
    stored = state["governance_receipts"][0]
    assert stored["digest"] == "sha256:governed"
    assert stored["governance_verdict"] == "ACCEPT"
    assert stored["drift_state"] == "clean"


def test_sdk_governance_receipt_exposes_proof_fields() -> None:
    if str(SDK_ROOT) not in sys.path:
        sys.path.insert(0, str(SDK_ROOT))
    from keyhole_sdk.models import GovernanceReceipt

    model = GovernanceReceipt.model_validate(
        {
            "digest": "sha256:governed",
            "status": "ACCEPT",
            "message": "Digest realized successfully.",
            "realized_at": "2026-06-09T00:00:00+00:00",
            "governed": True,
            "event_spine_evidence": True,
            "governance_verdict": "ACCEPT",
            "drift_state": "clean",
            "governance_context_id": "gctx_123",
            "mcp_event_id": "evt_123",
        }
    )

    assert model.governed is True
    assert model.event_spine_evidence is True
    assert model.governance_verdict == "ACCEPT"
    assert model.drift_state == "clean"
