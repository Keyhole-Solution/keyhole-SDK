"""Governed first-app demo flow for CE-V5-S51-C02.

This module wires the forkable ``my-first-app`` demo through the public MCP
boundary and local runtime bridge. It fails closed when required boundary
operations or governed receipt evidence are absent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
import yaml

from keyhole_sdk.models import GovernanceReceipt


REDACTED = "<redacted>"
STATE_DIRNAME = "governed-demo"
REGISTRATION_STATE = "registration.json"
CONTEXT_STATE = "context.json"
RECEIPT_STATE = "receipt.json"


class GovernedDemoError(RuntimeError):
    """Fail-closed error for governed demo operations."""


@dataclass
class BoundaryOperation:
    name: str
    path: str = ""
    method: str = "POST"


@dataclass
class GovernedDemoState:
    repo_path: Path
    state_dir: Path
    registration: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    receipt: Dict[str, Any] = field(default_factory=dict)


class GovernedFirstAppClient:
    """Client for the S51-C02 governed first-app flow."""

    def __init__(
        self,
        *,
        mcp_url: str,
        token: str,
        runtime_url: str = "http://localhost:8080",
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        if not mcp_url:
            raise GovernedDemoError("KEYHOLE_MCP_URL is required for governed demo flow.")
        if not token:
            raise GovernedDemoError("KEYHOLE_MCP_TOKEN is required for governed demo flow.")
        self.mcp_url = mcp_url.rstrip("/")
        self.runtime_url = runtime_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = session or requests.Session()
        self.capabilities: Dict[str, Any] = {}
        self.operations: Dict[str, BoundaryOperation] = {}

    @classmethod
    def from_env(
        cls,
        *,
        runtime_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> "GovernedFirstAppClient":
        return cls(
            mcp_url=os.environ.get("KEYHOLE_MCP_URL", ""),
            token=os.environ.get("KEYHOLE_MCP_TOKEN", ""),
            runtime_url=runtime_url or os.environ.get("KEYHOLE_RUNTIME_URL", "http://localhost:8080"),
            session=session,
        )

    def discover(self) -> Dict[str, BoundaryOperation]:
        response = self.session.get(
            f"{self.mcp_url}/mcp/v1/capabilities",
            timeout=self.timeout,
        )
        _raise_for_response(response, "capabilities discovery")
        data = _json_object(response)
        self.capabilities = data
        self.operations = _extract_operations(data)
        self._require_operations("repo.register", "context.compile")
        return dict(self.operations)

    def register_repo(self, repo_path: str | Path) -> Dict[str, Any]:
        self._ensure_discovered()
        op = self._require_operation("repo.register")
        repo = Path(repo_path).resolve()
        payload = _build_repo_registration_payload(repo)
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path or '/mcp/v1/repos/register'}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "repo registration")
        data = _json_object(response)
        registration_id = _first_string(
            data.get("registration_id"),
            data.get("repo_id"),
            data.get("id"),
            (data.get("result") or {}).get("registration_id") if isinstance(data.get("result"), dict) else "",
        )
        if not registration_id:
            raise GovernedDemoError("repo.register response missing registration_id/repo_id.")
        state = {
            "registration_id": registration_id,
            "repo": repo.name,
            "repo_path_digest": payload["repo"]["path_digest"],
            "boundary_operation": "repo.register",
            "upstream": _redact(data),
        }
        _write_state(repo, REGISTRATION_STATE, state)
        return state

    def compile_context(self, repo_path: str | Path) -> Dict[str, Any]:
        self._ensure_discovered()
        op = self._require_operation("context.compile")
        repo = Path(repo_path).resolve()
        registration = _read_state(repo, REGISTRATION_STATE)
        payload = {
            "run_type": "context.compile",
            "params": {
                "repo": repo.name,
                "registration_id": registration.get("registration_id", ""),
            },
        }
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path or '/mcp/v1/runs/start'}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "context compile")
        data = _json_object(response)
        context_id = _extract_context_id(data)
        if not context_id:
            raise GovernedDemoError("context.compile response missing governance_context_id or context digest.")
        state = {
            "governance_context_id": context_id,
            "repo": repo.name,
            "registration_id": registration.get("registration_id", ""),
            "boundary_operation": "context.compile",
            "upstream": _redact(data),
        }
        _write_state(repo, CONTEXT_STATE, state)
        return state

    def run_governed_realization(self, repo_path: str | Path) -> GovernanceReceipt:
        self._ensure_discovered()
        repo = Path(repo_path).resolve()
        context = _read_state(repo, CONTEXT_STATE)
        local_invariant = _run_local_invariant(repo)
        candidate_digest = _candidate_digest(repo, local_invariant, context)
        request = {
            "candidate_digest": candidate_digest,
            "require_governed": True,
            "governance_context_id": context.get("governance_context_id", ""),
            "local_invariant_result": local_invariant,
        }
        response = self.session.post(
            f"{self.runtime_url}/realize",
            json=request,
            timeout=self.timeout,
        )
        _raise_for_response(response, "governed runtime realization")
        data = _json_object(response)
        receipt = GovernanceReceipt.model_validate(data)
        _validate_governed_receipt(receipt)
        _write_state(repo, RECEIPT_STATE, _redact(receipt.model_dump(mode="json")))
        return receipt

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _ensure_discovered(self) -> None:
        if not self.operations:
            self.discover()

    def _require_operation(self, name: str) -> BoundaryOperation:
        self._require_operations(name)
        return self.operations[name]

    def _require_operations(self, *names: str) -> None:
        missing = [name for name in names if name not in self.operations]
        if missing:
            raise GovernedDemoError(
                "MCP capabilities missing required operation(s): " + ", ".join(missing)
            )


def _extract_operations(capabilities: Dict[str, Any]) -> Dict[str, BoundaryOperation]:
    found: Dict[str, BoundaryOperation] = {}

    def add(name: str, path: str = "", method: str = "POST") -> None:
        if name:
            found[name] = BoundaryOperation(name=name, path=path, method=method.upper())

    raw_ops = capabilities.get("operations")
    if isinstance(raw_ops, dict):
        for name, spec in raw_ops.items():
            if isinstance(spec, dict):
                add(str(name), str(spec.get("path", "")), str(spec.get("method", "POST")))
            elif spec:
                add(str(name))
    elif isinstance(raw_ops, list):
        for item in raw_ops:
            if isinstance(item, str):
                add(item)
            elif isinstance(item, dict):
                add(
                    str(item.get("name") or item.get("operation") or item.get("run_type") or ""),
                    str(item.get("path", "")),
                    str(item.get("method", "POST")),
                )

    for rt in _iter_run_types(capabilities):
        if rt == "context.compile":
            add("context.compile", "/mcp/v1/runs/start", "POST")
    return found


def _iter_run_types(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in ("run_type", "name", "operation") and isinstance(nested, str):
                yield nested
            else:
                yield from _iter_run_types(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_run_types(item)


def _build_repo_registration_payload(repo: Path) -> Dict[str, Any]:
    keyhole = _load_yaml(repo / "keyhole.yaml")
    contract = _load_yaml(repo / "governance_contract.yaml")
    passport = _load_yaml(repo / "capability_passport.yaml")
    dependencies = _load_yaml(repo / "dependencies.yaml")
    return {
        "repo": {
            "name": str(keyhole.get("repo") or repo.name),
            "path_digest": hashlib.sha256(str(repo).encode("utf-8")).hexdigest(),
        },
        "native_artifacts": {
            "keyhole": keyhole,
            "governance_contract": contract,
            "capability_passport": passport,
            "dependencies": dependencies,
        },
    }


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _run_local_invariant(repo: Path) -> Dict[str, Any]:
    gate = repo / "tests" / "invariants" / "inv_greet.py"
    if not gate.exists():
        raise GovernedDemoError(f"local invariant gate missing: {gate}")
    spec = importlib.util.spec_from_file_location("my_first_app_inv_greet", gate)
    if spec is None or spec.loader is None:
        raise GovernedDemoError("cannot load local invariant gate.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = module.run_gate()
    data = result.to_dict()
    if data.get("verdict") != "ACCEPT":
        raise GovernedDemoError("local invariant proof rejected; refusing governed realization.")
    return data


def _candidate_digest(repo: Path, invariant: Dict[str, Any], context: Dict[str, Any]) -> str:
    material = {
        "repo": repo.name,
        "invariant": invariant,
        "governance_context_id": context.get("governance_context_id", ""),
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_governed_receipt(receipt: GovernanceReceipt) -> None:
    if not receipt.governed:
        raise GovernedDemoError("runtime receipt did not report governed=true.")
    if not receipt.event_spine_evidence:
        raise GovernedDemoError("runtime receipt missing upstream event_spine_evidence=true.")
    if not receipt.governance_verdict:
        raise GovernedDemoError("runtime receipt missing governance_verdict.")
    if not receipt.drift_state:
        raise GovernedDemoError("runtime receipt missing drift_state.")
    if not receipt.governance_context_id:
        raise GovernedDemoError("runtime receipt missing governance_context_id.")
    if not receipt.mcp_event_id:
        raise GovernedDemoError("runtime receipt missing mcp_event_id or event pointer.")


def _extract_context_id(data: Dict[str, Any]) -> str:
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    keyhole = data.get("keyhole") if isinstance(data.get("keyhole"), dict) else {}
    return _first_string(
        data.get("governance_context_id"),
        data.get("ctxpack_digest"),
        data.get("digest"),
        data.get("ctx_ref_sha256"),
        result.get("governance_context_id"),
        result.get("ctxpack_digest"),
        inner.get("governance_context_id"),
        inner.get("ctxpack_digest"),
        keyhole.get("ctx_ref_sha256"),
    )


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def _json_object(response: requests.Response) -> Dict[str, Any]:
    data = response.json()
    if not isinstance(data, dict):
        raise GovernedDemoError("upstream response was not a JSON object.")
    return data


def _raise_for_response(response: requests.Response, action: str) -> None:
    if response.status_code >= 400:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("reason") or body.get("message") or body.get("detail") or "")
        except ValueError:
            detail = response.text[:200]
        raise GovernedDemoError(f"{action} failed with HTTP {response.status_code}: {detail}")


def _state_dir(repo: Path) -> Path:
    return repo / ".keyhole" / STATE_DIRNAME


def _write_state(repo: Path, filename: str, data: Dict[str, Any]) -> None:
    state_dir = _state_dir(repo)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / filename).write_text(json.dumps(_redact(data), indent=2), encoding="utf-8")


def _read_state(repo: Path, filename: str) -> Dict[str, Any]:
    path = _state_dir(repo) / filename
    if not path.exists():
        raise GovernedDemoError(f"missing governed demo state: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GovernedDemoError(f"invalid governed demo state: {path}")
    return data


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): (REDACTED if "token" in str(k).lower() or "authorization" in str(k).lower() else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value
