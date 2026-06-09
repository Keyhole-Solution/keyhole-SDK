from __future__ import annotations

from typing import Any, Dict, List


class FakeResponse:
    def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def json(self) -> Dict[str, Any]:
        return self._data


class FakeBoundarySession:
    def __init__(self, *, missing_operation: str = "") -> None:
        self.missing_operation = missing_operation
        self.calls: List[Dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        operations = {
            "repo.register": {"path": "/mcp/v1/repos/register", "method": "POST"},
            "context.compile": {"path": "/mcp/v1/runs/start", "method": "POST"},
        }
        operations.pop(self.missing_operation, None)
        return FakeResponse(200, {"operations": operations})

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if url.endswith("/mcp/v1/repos/register"):
            auth = kwargs.get("headers", {}).get("Authorization", "")
            if not auth.startswith("Bearer "):
                return FakeResponse(401, {"reason": "missing bearer token"})
            return FakeResponse(
                200,
                {
                    "registration_id": "reg_fake_123",
                    "repo_id": "repo_fake_123",
                    "status": "success",
                },
            )
        if url.endswith("/mcp/v1/runs/start"):
            payload = kwargs.get("json", {})
            if payload.get("run_type") != "context.compile":
                return FakeResponse(400, {"reason": "unsupported run_type"})
            return FakeResponse(
                200,
                {
                    "status": "success",
                    "result": {
                        "governance_context_id": "gctx_fake_123",
                    },
                },
            )
        return FakeResponse(404, {"reason": "unknown path"})

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        if url.endswith("/realize"):
            payload = kwargs.get("json", {})
            if not payload.get("require_governed"):
                return FakeResponse(400, {"reason": "require_governed missing"})
            return FakeResponse(
                200,
                {
                    "digest": payload["candidate_digest"],
                    "status": "ACCEPT",
                    "message": "Digest realized successfully.",
                    "realized_at": "2026-06-09T00:00:00+00:00",
                    "governed": True,
                    "event_spine_evidence": True,
                    "governance_verdict": "ACCEPT",
                    "drift_state": "clean",
                    "governance_context_id": payload["governance_context_id"],
                    "mcp_event_id": "evt_fake_123",
                    "proof_id": "proof_fake_123",
                    "receipt_id": "receipt_fake_123",
                },
            )
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        pass
