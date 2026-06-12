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
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests

from keyhole_sdk.models import GovernanceReceipt


REDACTED = "<redacted>"
STATE_DIRNAME = "governed-demo"
REGISTRATION_STATE = "registration.json"
CONTEXT_STATE = "context.json"
RECEIPT_STATE = "receipt.json"
GAP_ID = "CE-V5-S51-C02"
STORY_ID = "CE-V5-S51-C02"
GAP_ID_OVERRIDE_ENV = "KEYHOLE_C02_GAP_ID"
ASYNC_TERMINAL_STATUSES = {"completed", "succeeded", "success", "failed", "canceled", "cancelled", "timed_out"}
ASYNC_ACTIVE_STATUSES = {"accepted", "queued", "pending", "running", "started"}


class GovernedDemoError(RuntimeError):
    """Fail-closed error for governed demo operations."""


@dataclass
class BoundaryOperation:
    name: str
    path: str = ""
    method: str = "POST"
    surface: str = "http"
    run_type: str = ""


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
        self.raw_capabilities: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}
        self.operations: Dict[str, BoundaryOperation] = {}
        self.resolved_gap_id: str = ""
        self.gap_id_source: str = ""

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
        raw = _json_object(response)
        data = _unwrap_mcp_envelope(raw)
        self.raw_capabilities = raw
        self.capabilities = data
        self.operations = _extract_operations(raw)
        if _requires_active_claim(data):
            self._require_operations("gaps.claim")
        self._require_operations("repo.register", "context.compile", "governed.realize")
        return dict(self.operations)

    def register_repo(self, repo_path: str | Path) -> Dict[str, Any]:
        self._ensure_discovered()
        op = self._require_operation("repo.register")
        repo = Path(repo_path).resolve()
        claim = self.claim_gap(repo) if _requires_active_claim(self.capabilities) else {}
        payload = _build_repo_registration_payload(repo, op, claim=claim)
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "repo registration")
        data = _json_object(response)
        _raise_for_mcp_error(data, "repo registration")
        data = self._resolve_async_result(data, "repo registration")
        registration_id = _first_string(
            data.get("registration_id"),
            data.get("repo_id"),
            data.get("declaration_id"),
            data.get("governance_context_id"),
            data.get("ctxpack_digest"),
            data.get("id"),
            (data.get("result") or {}).get("registration_id") if isinstance(data.get("result"), dict) else "",
            (data.get("result") or {}).get("repo_id") if isinstance(data.get("result"), dict) else "",
            (data.get("result") or {}).get("declaration_id") if isinstance(data.get("result"), dict) else "",
            (data.get("result") or {}).get("governance_context_id") if isinstance(data.get("result"), dict) else "",
            (data.get("result") or {}).get("ctxpack_digest") if isinstance(data.get("result"), dict) else "",
            (data.get("data") or {}).get("registration_id") if isinstance(data.get("data"), dict) else "",
            (data.get("data") or {}).get("repo_id") if isinstance(data.get("data"), dict) else "",
            (data.get("data") or {}).get("declaration_id") if isinstance(data.get("data"), dict) else "",
            (data.get("data") or {}).get("governance_context_id") if isinstance(data.get("data"), dict) else "",
            (data.get("data") or {}).get("ctxpack_digest") if isinstance(data.get("data"), dict) else "",
            ((data.get("data") or {}).get("result") or {}).get("registration_id")
            if isinstance((data.get("data") or {}).get("result"), dict) else "",
            ((data.get("data") or {}).get("result") or {}).get("declaration_id")
            if isinstance((data.get("data") or {}).get("result"), dict) else "",
        )
        if not registration_id:
            raise GovernedDemoError(
                "repo.register response missing registration_id/repo_id/declaration_id/governance_context_id."
            )
        state = {
            "registration_id": registration_id,
            "repo": repo.name,
            "repo_path_digest": hashlib.sha256(str(repo).encode("utf-8")).hexdigest(),
            "boundary_operation": op.name,
            "path": op.path,
            "run_type": op.run_type,
            "claim_id": claim.get("claim_id", ""),
            "claim_ref": claim.get("claim_ref", ""),
            "gap_id": claim.get("gap_id", GAP_ID),
            "story_id": STORY_ID,
            "gap_id_source": self.gap_id_source,
            "upstream": _redact(data),
        }
        _write_state(repo, REGISTRATION_STATE, state)
        return state

    def claim_gap(self, repo_path: str | Path) -> Dict[str, Any]:
        self._ensure_discovered()
        op = self._require_operation("gaps.claim")
        repo = Path(repo_path).resolve()
        metadata = _repo_git_metadata(repo)
        ctxpack_digest = self._compile_preclaim_context(repo)
        gap_id = self._resolve_gap_id(repo)
        payload = {
            "run_type": op.run_type or "gaps.claim",
            "ctxpack_digest": ctxpack_digest,
            "params": {
                "gap_id": gap_id,
                "story_id": STORY_ID,
                "ctxpack_digest": ctxpack_digest,
                "purpose": "governed first-app live verifier",
                "repo_remote": metadata["repo_remote"],
                "commit_sha": metadata["commit_sha"],
                "branch": metadata.get("branch", ""),
            },
        }
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "gap claim")
        data = _json_object(response)
        _raise_for_mcp_error(data, "gap claim")
        data = self._resolve_async_result(data, "gap claim")
        claim_id = _extract_claim_id(data)
        claim_ref = _extract_claim_ref(data)
        if not claim_id and not claim_ref:
            raise GovernedDemoError("gap claim response missing claim_id/claim_ref.")
        return {
            "claim_id": claim_id,
            "claim_ref": claim_ref,
            "gap_id": gap_id,
            "gap_id_source": self.gap_id_source,
            "upstream": _redact(data),
        }

    def _resolve_gap_id(self, repo: Path) -> str:
        if self.resolved_gap_id:
            return self.resolved_gap_id
        override = os.environ.get(GAP_ID_OVERRIDE_ENV, "").strip()
        if override:
            if not override.startswith("gap_"):
                raise GovernedDemoError(f"{GAP_ID_OVERRIDE_ENV} must be a canonical gap_* id.")
            self.resolved_gap_id = override
            self.gap_id_source = f"diagnostic override {GAP_ID_OVERRIDE_ENV}"
            return override
        explicit = _gap_id_from_capabilities(self.capabilities)
        if explicit:
            self.resolved_gap_id = explicit
            self.gap_id_source = "capabilities"
            return explicit
        discovered = self._discover_gap_id(repo)
        if discovered:
            self.resolved_gap_id = discovered
            self.gap_id_source = "gaps.list"
            return discovered
        raise GovernedDemoError(
            "cannot resolve canonical claimable gap_id for story_id=CE-V5-S51-C02; "
            "capabilities did not provide one and gaps.list returned no matching gap."
        )

    def _discover_gap_id(self, repo: Path) -> str:
        op = _gap_discovery_operation(self.capabilities)
        payload = {
            "run_type": op.run_type,
            "params": {
                "status": "*",
                "limit": 50,
                "order_by": "actionable",
                "story_id": STORY_ID,
                "repo": repo.name,
                "repo_name": repo.name,
                "domain": repo.name,
                "fingerprint_version": "sdk-v1",
            },
        }
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "gap discovery")
        data = _json_object(response)
        _raise_for_mcp_error(data, "gap discovery")
        data = self._resolve_async_result(data, "gap discovery")
        return _select_gap_id(data, repo.name)

    def _compile_preclaim_context(self, repo: Path) -> str:
        op = self._require_operation("context.compile")
        payload = {
            "run_type": op.run_type or "context.compile",
            "params": {
                "repo": repo.name,
                "gap_id": GAP_ID,
            },
        }
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "pre-claim context compile")
        data = _json_object(response)
        _raise_for_mcp_error(data, "pre-claim context compile")
        data = self._resolve_async_result(data, "pre-claim context compile")
        context_id = _extract_context_id(data)
        if not context_id:
            raise GovernedDemoError("pre-claim context.compile response missing ctxpack digest.")
        return context_id

    def compile_context(self, repo_path: str | Path) -> Dict[str, Any]:
        self._ensure_discovered()
        op = self._require_operation("context.compile")
        repo = Path(repo_path).resolve()
        registration = _read_state(repo, REGISTRATION_STATE)
        payload = {
            "run_type": op.run_type or "context.compile",
            "params": {
                "repo": repo.name,
                "registration_id": registration.get("registration_id", ""),
                "gap_id": registration.get("gap_id") or GAP_ID,
                "story_id": STORY_ID,
            },
        }
        response = self.session.request(
            op.method,
            f"{self.mcp_url}{op.path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        _raise_for_response(response, "context compile")
        data = _json_object(response)
        _raise_for_mcp_error(data, "context compile")
        data = self._resolve_async_result(data, "context compile")
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
        op = self._require_operation("governed.realize")
        request = {
            "run_type": op.run_type or "governed.realize",
            "params": {
                "candidate_digest": candidate_digest,
                "require_governed": True,
                "governance_context_id": context.get("governance_context_id", ""),
                "local_invariant_result": local_invariant,
            },
        }
        if op.surface == "runtime":
            runtime_request = dict(request["params"])
            response = self.session.post(
                f"{self.runtime_url}/realize",
                json=runtime_request,
                timeout=self.timeout,
            )
        else:
            response = self.session.request(
                op.method,
                f"{self.mcp_url}{op.path}",
                headers=self._headers(),
                json=request,
                timeout=self.timeout,
            )
        _raise_for_response(response, "governed runtime realization")
        data = _json_object(response)
        _raise_for_mcp_error(data, "governed runtime realization")
        data = self._resolve_async_result(data, "governed runtime realization")
        receipt = GovernanceReceipt.model_validate(_normalize_governance_receipt(data, candidate_digest))
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

    def _resolve_async_result(self, data: Dict[str, Any], action: str) -> Dict[str, Any]:
        inner = data.get("data") if isinstance(data.get("data"), dict) else {}
        status = _first_string(inner.get("status"), data.get("status")).lower()
        if status not in ASYNC_ACTIVE_STATUSES:
            return data
        run_id = _first_string(inner.get("run_id"), data.get("run_id"))
        poll_url = _first_string(inner.get("poll_url"), data.get("poll_url"))
        if not run_id and not poll_url:
            raise GovernedDemoError(f"{action} accepted asynchronously but returned no run_id or poll_url.")
        paths = []
        if poll_url:
            paths.append(poll_url)
        if run_id:
            paths.append(f"/mcp/v1/runs/{run_id}/status")
        deadline = time.monotonic() + max(self.timeout, 120.0)
        last: Dict[str, Any] = data
        while time.monotonic() < deadline:
            for path in dict.fromkeys(paths):
                response = self.session.get(
                    f"{self.mcp_url}{path}",
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                _raise_for_response(response, f"{action} status poll")
                polled = _json_object(response)
                _raise_for_mcp_error(polled, f"{action} status poll")
                last = polled
                polled_data = polled.get("data") if isinstance(polled.get("data"), dict) else {}
                polled_status = _first_string(polled_data.get("status"), polled.get("status")).lower()
                if polled_status in ASYNC_TERMINAL_STATUSES or polled_data.get("is_terminal") is True:
                    if polled_status in {"failed", "canceled", "cancelled", "timed_out"}:
                        error = polled_data.get("error") if isinstance(polled_data.get("error"), dict) else {}
                        code = _first_string(error.get("code"), polled_data.get("terminal_reason"))
                        message = _first_string(error.get("message"), code)
                        raise GovernedDemoError(f"{action} failed: {code}: {message}")
                    return polled
            time.sleep(2)
        raise GovernedDemoError(f"{action} did not reach a terminal run status before timeout: {_redact(last)}")


def _extract_operations(capabilities: Dict[str, Any]) -> Dict[str, BoundaryOperation]:
    found: Dict[str, BoundaryOperation] = {}

    def add(
        name: str,
        path: str = "",
        method: str = "POST",
        *,
        surface: str = "http",
        run_type: str = "",
    ) -> None:
        if name:
            if not path and (surface == "runs.start" or run_type):
                path = "/mcp/v1/runs/start"
            if path == "/realize":
                surface = "runtime"
            found[name] = BoundaryOperation(
                name=name,
                path=path,
                method=method.upper(),
                surface=surface,
                run_type=run_type,
            )

    data = _unwrap_mcp_envelope(capabilities)
    for raw_ops in (capabilities.get("operations"), data.get("operations")):
        if isinstance(raw_ops, dict):
            for name, spec in raw_ops.items():
                if isinstance(spec, dict):
                    add(
                        str(name),
                        str(spec.get("path", "")),
                        str(spec.get("method", "POST")),
                        surface=str(spec.get("surface", "http")),
                        run_type=str(spec.get("run_type", "")),
                    )
                elif spec:
                    add(str(name), "/mcp/v1/runs/start" if str(name).endswith(".realize") else "")
        elif isinstance(raw_ops, list):
            for item in raw_ops:
                if isinstance(item, str):
                    add(item)
                elif isinstance(item, dict):
                    path = str(item.get("path", ""))
                    method = str(item.get("method", "POST"))
                    operation_id = str(item.get("operation_id") or item.get("name") or item.get("operation") or "")
                    run_type = str(item.get("run_type") or "")
                    if operation_id and not item.get("run_types"):
                        add(operation_id, path, method, run_type=run_type)
                    run_types = item.get("run_types")
                    if isinstance(run_types, list):
                        for rt in run_types:
                            if isinstance(rt, str):
                                logical = _logical_name_for_run_type(rt)
                                add(logical, path, method, surface=operation_id or "runs.start", run_type=rt)

    sdk = data.get("governed_worker_sdk") if isinstance(data.get("governed_worker_sdk"), dict) else {}
    repo_governance = sdk.get("repo_governance") if isinstance(sdk.get("repo_governance"), dict) else {}
    canonical = str(repo_governance.get("canonical_run_type") or "")
    aliases = repo_governance.get("logical_aliases")
    if canonical:
        for alias in aliases if isinstance(aliases, list) else ["repo.register"]:
            if isinstance(alias, str):
                add(alias, "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=canonical)
        add("repo.register", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=canonical)

    logical_map = sdk.get("logical_operation_map") if isinstance(sdk.get("logical_operation_map"), dict) else {}
    for key, spec in logical_map.items():
        if not isinstance(spec, dict):
            continue
        run_type = str(spec.get("run_type") or "")
        path = str(spec.get("path") or "")
        method = str(spec.get("method") or "POST")
        surface = str(spec.get("surface") or spec.get("kind") or "runs.start")
        names = [str(key)]
        equivalents = spec.get("equivalent_to")
        if isinstance(equivalents, list):
            names.extend(str(item) for item in equivalents if isinstance(item, str))
        if run_type:
            names.append(_logical_name_for_run_type(run_type))
        for name in names:
            add(name, path, method, surface=surface, run_type=run_type)

    compile_block = sdk.get("governed_context_compile") if isinstance(sdk.get("governed_context_compile"), dict) else {}
    compile_rt = str(compile_block.get("canonical_run_type") or "")
    if compile_rt:
        add("context.compile", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=compile_rt)

    realize = logical_map.get("governed_realization") if isinstance(logical_map.get("governed_realization"), dict) else {}
    realize_rt = str(realize.get("run_type") or "")
    if realize_rt:
        add("governed.realize", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=realize_rt)

    for rt in _iter_run_types(data):
        if rt in {"governance.context.create", "repo.register", "participant.declare", "worker.repo.register"}:
            add("repo.register", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=rt)
        elif rt == "context.compile":
            add("context.compile", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=rt)
        elif rt == "governed.realize":
            add("governed.realize", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=rt)
        elif rt == "gaps.claim":
            add("gaps.claim", "/mcp/v1/runs/start", "POST", surface="runs.start", run_type=rt)

    return found


def _logical_name_for_run_type(run_type: str) -> str:
    if run_type in {"governance.context.create", "repo.register", "participant.declare", "worker.repo.register"}:
        return "repo.register"
    if run_type == "gaps.claim":
        return "gaps.claim"
    if run_type == "context.compile":
        return "context.compile"
    if run_type == "governed.realize":
        return "governed.realize"
    return run_type


def _unwrap_mcp_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("ok") is True and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def _extract_legacy_operations(capabilities: Dict[str, Any]) -> Dict[str, BoundaryOperation]:
    found: Dict[str, BoundaryOperation] = {}
    raw_ops = capabilities.get("operations")
    if isinstance(raw_ops, dict):
        for name, spec in raw_ops.items():
            if isinstance(spec, dict):
                found[str(name)] = BoundaryOperation(str(name), str(spec.get("path", "")), str(spec.get("method", "POST")))
            elif spec:
                found[str(name)] = BoundaryOperation(str(name))
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
            if isinstance(item, str):
                yield item
            else:
                yield from _iter_run_types(item)


def _requires_active_claim(capabilities: Dict[str, Any]) -> bool:
    sdk = capabilities.get("governed_worker_sdk") if isinstance(capabilities.get("governed_worker_sdk"), dict) else {}
    repo_governance = sdk.get("repo_governance") if isinstance(sdk.get("repo_governance"), dict) else {}
    return repo_governance.get("requires_active_claim") is True


def _gap_id_from_capabilities(capabilities: Dict[str, Any]) -> str:
    sdk = capabilities.get("governed_worker_sdk") if isinstance(capabilities.get("governed_worker_sdk"), dict) else {}
    candidates = [
        sdk.get("canonical_gap_id"),
        sdk.get("gap_id"),
    ]
    for block_name in ("gap_claim", "repo_governance"):
        block = sdk.get(block_name) if isinstance(sdk.get(block_name), dict) else {}
        candidates.extend([
            block.get("canonical_gap_id"),
            block.get("gap_id"),
        ])
        resolution = block.get("gap_id_resolution") if isinstance(block.get("gap_id_resolution"), dict) else {}
        candidates.extend([
            resolution.get("canonical_gap_id"),
            resolution.get("gap_id"),
        ])
        prerequisite = block.get("gap_prerequisite") if isinstance(block.get("gap_prerequisite"), dict) else {}
        candidates.extend([
            prerequisite.get("canonical_gap_id"),
            prerequisite.get("gap_id"),
        ])
    for value in candidates:
        if isinstance(value, str) and value.startswith("gap_"):
            return value
    return ""


def _gap_discovery_operation(capabilities: Dict[str, Any]) -> BoundaryOperation:
    sdk = capabilities.get("governed_worker_sdk") if isinstance(capabilities.get("governed_worker_sdk"), dict) else {}
    logical_map = sdk.get("logical_operation_map") if isinstance(sdk.get("logical_operation_map"), dict) else {}
    discovery = logical_map.get("gap_discovery") if isinstance(logical_map.get("gap_discovery"), dict) else {}
    run_type = str(discovery.get("start_with_run_type") or discovery.get("run_type") or "")
    if not run_type:
        claim = sdk.get("gap_claim") if isinstance(sdk.get("gap_claim"), dict) else {}
        resolution = claim.get("gap_id_resolution") if isinstance(claim.get("gap_id_resolution"), dict) else {}
        run_type = str(resolution.get("start_here_run_type") or "")
    if not run_type:
        raise GovernedDemoError("MCP capabilities missing gap discovery run type.")
    return BoundaryOperation(
        name="gap_discovery",
        path=str(discovery.get("path") or "/mcp/v1/runs/start"),
        method=str(discovery.get("method") or "POST"),
        surface=str(discovery.get("surface") or "runs.start"),
        run_type=run_type,
    )


def _select_gap_id(data: Dict[str, Any], repo_name: str) -> str:
    gaps = list(_iter_gap_objects(data))
    if not gaps:
        return ""

    def score(gap: Dict[str, Any]) -> int:
        raw = json.dumps(gap, sort_keys=True).lower()
        value = 0
        if STORY_ID.lower() in raw:
            value += 100
        if repo_name.lower() in raw:
            value += 20
        if "sdk-v1" in raw:
            value += 10
        status = str(gap.get("status") or gap.get("state") or "").lower()
        if status in {"open", "claimable", "actionable", "claimed"}:
            value += 5
        return value

    ranked = sorted(gaps, key=score, reverse=True)
    best = ranked[0]
    if score(best) <= 0:
        return ""
    return _first_string(best.get("gap_id"), best.get("id"))


def _iter_gap_objects(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        gap_id = _first_string(value.get("gap_id"), value.get("id"))
        if gap_id.startswith("gap_"):
            yield value
        for nested in value.values():
            yield from _iter_gap_objects(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_gap_objects(item)


def _build_repo_registration_payload(
    repo: Path,
    op: BoundaryOperation,
    *,
    claim: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    keyhole = _load_yaml(repo / "keyhole.yaml")
    contract = _load_yaml(repo / "governance_contract.yaml")
    passport = _load_yaml(repo / "capability_passport.yaml")
    dependencies = _load_yaml(repo / "dependencies.yaml")
    native_artifacts = {
        "keyhole": keyhole,
        "governance_contract": contract,
        "capability_passport": passport,
        "dependencies": dependencies,
    }
    legacy_payload = {
        "repo": {
            "name": str(keyhole.get("repo") or repo.name),
            "path_digest": hashlib.sha256(str(repo).encode("utf-8")).hexdigest(),
        },
        "native_artifacts": native_artifacts,
    }
    if not op.run_type:
        return legacy_payload
    metadata = _repo_git_metadata(repo)
    params = {
        "gap_id": str((claim or {}).get("gap_id") or GAP_ID),
        "story_id": STORY_ID,
        "repo_name": str(keyhole.get("repo") or repo.name),
        "repo_remote": metadata["repo_remote"],
        "commit_sha": metadata["commit_sha"],
        "branch": metadata.get("branch", ""),
        "declared_repo_class": str(keyhole.get("repo_class") or "SDK_TEMPLATE"),
        "purpose": "CE-V5-S51-C02 governed first app live verifier",
        "origin": "keyhole-sdk",
        "declaration_files": {
            "keyhole_yaml_digest": _file_digest(repo / "keyhole.yaml"),
            "governance_contract_digest": _file_digest(repo / "governance_contract.yaml"),
            "capability_passport_digest": _file_digest(repo / "capability_passport.yaml"),
            "dependencies_digest": _file_digest(repo / "dependencies.yaml"),
        },
        "native_artifacts": native_artifacts,
    }
    if claim:
        if claim.get("claim_id"):
            params["claim_id"] = claim["claim_id"]
        if claim.get("claim_ref"):
            params["claim_ref"] = claim["claim_ref"]
    return {
            "run_type": op.run_type,
            "params": params,
        }


def _repo_git_metadata(repo: Path) -> Dict[str, str]:
    repo_remote = _git_value(repo, "remote", "get-url", "origin")
    commit_sha = _git_value(repo, "rev-parse", "HEAD")
    branch = _git_value(repo, "branch", "--show-current")
    missing = []
    if not repo_remote:
        missing.append("repo_remote")
    if not commit_sha:
        missing.append("commit_sha")
    if missing:
        raise GovernedDemoError(
            "cannot build governance.context.create params; missing required git field(s): "
            + ", ".join(missing)
        )
    return {
        "repo_remote": repo_remote,
        "commit_sha": commit_sha,
        "branch": branch,
    }


def _file_digest(path: Path) -> str:
    if not path.exists():
        return ""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_value(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise GovernedDemoError(
            "PyYAML is required to read Keyhole declaration files. "
            "Install the SDK dependencies with: pip install -e packages/python/keyhole-sdk"
        ) from exc
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
    if receipt.governance_verdict != "ACCEPT":
        raise GovernedDemoError("runtime receipt missing governance_verdict=ACCEPT.")
    if not receipt.drift_state:
        raise GovernedDemoError("runtime receipt missing drift_state.")
    if not receipt.governance_context_id:
        raise GovernedDemoError("runtime receipt missing governance_context_id.")
    if not receipt.mcp_event_id:
        raise GovernedDemoError("runtime receipt missing mcp_event_id or event pointer.")


def _normalize_governance_receipt(data: Dict[str, Any], candidate_digest: str) -> Dict[str, Any]:
    normalized = _unwrap_mcp_envelope(data)
    result = normalized.get("result") if isinstance(normalized.get("result"), dict) else {}
    inner = normalized.get("data") if isinstance(normalized.get("data"), dict) else {}
    receipt = result.get("receipt") if isinstance(result.get("receipt"), dict) else {}
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}

    governed = _first_bool(
        normalized.get("governed"),
        result.get("governed"),
        inner.get("governed"),
        receipt.get("governed"),
    )
    event_pointer = _first_string(
        normalized.get("mcp_event_id"),
        normalized.get("mcp_event_pointer"),
        normalized.get("event_id"),
        result.get("mcp_event_id"),
        result.get("mcp_event_pointer"),
        result.get("event_id"),
        result.get("event_pointer"),
        inner.get("mcp_event_id"),
        inner.get("mcp_event_pointer"),
        receipt.get("mcp_event_id"),
        receipt.get("mcp_event_pointer"),
        evidence.get("event_id"),
        evidence.get("event_pointer"),
    )
    return {
        "digest": _first_string(normalized.get("digest"), result.get("digest"), inner.get("digest"), candidate_digest),
        "status": _first_string(normalized.get("status"), result.get("status"), inner.get("status"), "ACCEPT"),
        "message": _first_string(normalized.get("message"), result.get("message"), inner.get("message")),
        "realized_at": _first_string(
            normalized.get("realized_at"),
            result.get("realized_at"),
            inner.get("realized_at"),
            datetime.now(timezone.utc).isoformat(),
        ),
        "governed": governed,
        "event_spine_evidence": _first_bool(
            normalized.get("event_spine_evidence"),
            result.get("event_spine_evidence"),
            inner.get("event_spine_evidence"),
            receipt.get("event_spine_evidence"),
        ),
        "governance_verdict": _first_string(
            normalized.get("governance_verdict"),
            normalized.get("verdict"),
            result.get("governance_verdict"),
            result.get("verdict"),
            inner.get("governance_verdict"),
            receipt.get("governance_verdict"),
            receipt.get("verdict"),
        ),
        "drift_state": _first_string(
            normalized.get("drift_state"),
            result.get("drift_state"),
            inner.get("drift_state"),
            receipt.get("drift_state"),
        ),
        "governance_context_id": _first_string(
            normalized.get("governance_context_id"),
            result.get("governance_context_id"),
            inner.get("governance_context_id"),
            receipt.get("governance_context_id"),
        ),
        "mcp_event_id": event_pointer,
        "proof_id": _first_string(normalized.get("proof_id"), result.get("proof_id"), receipt.get("proof_id")),
        "receipt_id": _first_string(
            normalized.get("receipt_id"),
            result.get("receipt_id"),
            receipt.get("receipt_id"),
            normalized.get("run_id"),
        ),
        "passport_digest": _first_string(
            normalized.get("passport_digest"),
            result.get("passport_digest"),
            receipt.get("passport_digest"),
        ),
        "trust_digest": _first_string(normalized.get("trust_digest"), result.get("trust_digest"), receipt.get("trust_digest")),
    }


def _extract_context_id(data: Dict[str, Any]) -> str:
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    keyhole = data.get("keyhole") if isinstance(data.get("keyhole"), dict) else {}
    run = inner.get("run") if isinstance(inner.get("run"), dict) else {}
    run_result = run.get("result") if isinstance(run.get("result"), dict) else {}
    nested_result = inner.get("result") if isinstance(inner.get("result"), dict) else {}
    context_card = run_result.get("context_card") if isinstance(run_result.get("context_card"), dict) else {}
    determinism = context_card.get("determinism") if isinstance(context_card.get("determinism"), dict) else {}
    return _first_string(
        data.get("governance_context_id"),
        data.get("ctxpack_digest"),
        data.get("digest"),
        data.get("ctx_ref_sha256"),
        result.get("governance_context_id"),
        result.get("ctxpack_digest"),
        inner.get("governance_context_id"),
        inner.get("ctxpack_digest"),
        nested_result.get("governance_context_id"),
        nested_result.get("ctxpack_digest"),
        run_result.get("governance_context_id"),
        run_result.get("ctxpack_digest"),
        run_result.get("ctx_ref_sha256"),
        determinism.get("digest"),
        keyhole.get("ctx_ref_sha256"),
    )


def _extract_claim_id(data: Dict[str, Any]) -> str:
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    nested_result = inner.get("result") if isinstance(inner.get("result"), dict) else {}
    run = inner.get("run") if isinstance(inner.get("run"), dict) else {}
    return _first_string(
        data.get("claim_id"),
        result.get("claim_id"),
        inner.get("claim_id"),
        nested_result.get("claim_id"),
        run.get("claim_id"),
    )


def _extract_claim_ref(data: Dict[str, Any]) -> str:
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    nested_result = inner.get("result") if isinstance(inner.get("result"), dict) else {}
    run = inner.get("run") if isinstance(inner.get("run"), dict) else {}
    return _first_string(
        data.get("claim_ref"),
        data.get("claim_token"),
        result.get("claim_ref"),
        result.get("claim_token"),
        inner.get("claim_ref"),
        inner.get("claim_token"),
        nested_result.get("claim_ref"),
        nested_result.get("claim_token"),
        run.get("claim_ref"),
    )


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def _first_bool(*values: Any) -> bool:
    for value in values:
        if isinstance(value, bool):
            return value
    return False


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


def _raise_for_mcp_error(data: Dict[str, Any], action: str) -> None:
    if data.get("ok") is not False:
        return
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    code = _first_string(error.get("code"), inner.get("code"))
    message = _first_string(error.get("message"), inner.get("message"), data.get("message"))
    detail = f"{code}: {message}" if code and message else code or message or "MCP returned ok=false"
    raise GovernedDemoError(f"{action} rejected by MCP: {detail}")


def _raise_for_async_acceptance(data: Dict[str, Any], action: str) -> None:
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    status = _first_string(inner.get("status"), data.get("status")).lower()
    if status not in {"accepted", "queued", "pending", "running", "started"}:
        return
    run_id = _first_string(inner.get("run_id"), data.get("run_id"))
    poll_url = _first_string(inner.get("poll_url"), data.get("poll_url"))
    detail = f"run_id={run_id or '<missing>'}"
    if poll_url:
        detail += f", poll_url={poll_url}"
    raise GovernedDemoError(
        f"{action} accepted asynchronously but did not return a terminal result inline ({detail}). "
        "The live verifier requires the MCP run status endpoint to return the completed result before it can proceed."
    )


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
