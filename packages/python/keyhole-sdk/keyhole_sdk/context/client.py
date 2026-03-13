"""Governed context retrieval client.

CE-V5-S42-05: Governed Context Retrieval Bootstrap.

Invokes current read-only context-access surfaces through MCP via
``POST /mcp/v1/runs/start``.  Returns normalized
:class:`ContextSnapshot` instances that downstream consumers can
rely on without inspecting raw JSON.

Supported context-access run types (as disclosed by the boundary):
  - ``context.compile``
  - ``gaps.list``
  - ``lineage.get.v0_1``
  - ``convergence.status.v0_1``

Failure mode: fail clearly when retrieval fails or response shape
is unusable.  Do not fabricate context.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from keyhole_sdk.exceptions import (
    AuthenticationError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.context.models import (
    ContextAccessInfo,
    ContextSnapshot,
    ContractInfo,
    GuidanceInfo,
    InterfaceInfo,
    RetrievalMetadata,
    RunStartRequest,
    RunStartResponse,
    TopologyInfo,
)


DEFAULT_CONTEXT_TIMEOUT = 30.0
RUNS_START_PATH = "/mcp/v1/runs/start"

# Currently implemented read-only context-access run types.
# Do not guess additional surfaces — use exact canonical keys only.
CONTEXT_RUN_TYPES = frozenset({
    "context.compile",
    "gaps.list",
    "lineage.get.v0_1",
    "convergence.status.v0_1",
})


class ContextClient:
    """Governed context retrieval client.

    Invokes read-only context-access run types through the MCP
    boundary and normalizes the response into a stable local
    :class:`ContextSnapshot`.

    Usage::

        client = ContextClient(
            base_url="https://boundary.example.com",
            token="<bearer-token>",
        )
        snapshot = client.compile_context()
        print(snapshot.get_platform_name())
        print(snapshot.get_implemented_surfaces())
        client.close()

    Or as a context manager::

        with ContextClient(base_url=url, token=token) as ctx:
            snapshot = ctx.compile_context()
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        timeout: float = DEFAULT_CONTEXT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = "keyhole-sdk-context"
        self._session.headers["Authorization"] = f"Bearer {token}"

    # ── High-level surface methods ──────────────────────────

    def compile_context(self, **params: Any) -> ContextSnapshot:
        """Invoke ``context.compile`` and return a normalized snapshot.

        This is the primary context bootstrap surface.  Use it when
        the participant needs the broadest current platform context
        bundle.
        """
        return self._invoke_and_normalize("context.compile", params)

    def list_gaps(self, **params: Any) -> RunStartResponse:
        """Invoke ``gaps.list`` and return the raw response.

        Use when the participant needs to browse current gaps or
        understand open work posture.
        """
        return self._invoke("gaps.list", params)

    def get_lineage(self, target: str, **params: Any) -> RunStartResponse:
        """Invoke ``lineage.get.v0_1`` for a known target.

        Use when the participant needs causal lineage information.
        """
        params["target"] = target
        return self._invoke("lineage.get.v0_1", params)

    def get_convergence_status(self, **params: Any) -> RunStartResponse:
        """Invoke ``convergence.status.v0_1`` and return the response.

        Use when the participant needs current convergence posture.
        """
        return self._invoke("convergence.status.v0_1", params)

    # ── Generic invocation ──────────────────────────────────

    def invoke(self, run_type: str, params: Optional[Dict[str, Any]] = None) -> RunStartResponse:
        """Invoke an arbitrary context-access run type.

        Only currently implemented context-access run types are
        accepted.  Raises ``ValueError`` for unknown run types.
        """
        if run_type not in CONTEXT_RUN_TYPES:
            raise ValueError(
                f"Unknown context-access run type: {run_type!r}. "
                f"Supported: {sorted(CONTEXT_RUN_TYPES)}"
            )
        return self._invoke(run_type, params or {})

    # ── Internal helpers ────────────────────────────────────

    def _invoke(self, run_type: str, params: Dict[str, Any]) -> RunStartResponse:
        """Perform ``POST /mcp/v1/runs/start`` and return parsed response."""
        url = f"{self.base_url}{RUNS_START_PATH}"
        payload = {"run_type": run_type, "params": params}

        try:
            response = self._session.post(
                url, json=payload, timeout=self.timeout
            )
        except (requests.ConnectionError, requests.Timeout, OSError) as exc:
            raise TransportError(
                f"Context retrieval failed for {run_type}: {exc}"
            ) from exc

        if response.status_code == 401:
            raise AuthenticationError(
                f"Authentication required for {run_type}. "
                "Ensure a valid bearer token is provided."
            )

        if response.status_code == 403:
            raise AuthenticationError(
                f"Insufficient authority for {run_type}. "
                "Check participant identity and charter posture."
            )

        if response.status_code not in (200, 201, 202):
            raise TransportError(
                f"Context retrieval returned {response.status_code} "
                f"for {run_type}: {response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise SchemaError(
                f"Context response for {run_type} is not valid JSON",
                raw_data=None,
            ) from exc

        if not isinstance(data, dict):
            raise SchemaError(
                f"Context response for {run_type} is not a JSON object",
                raw_data=None,
            )

        return RunStartResponse(
            run_type=run_type,
            status=_safe_str(data, "status"),
            data=_safe_dict(data, "data"),
            raw=data,
        )

    def _invoke_and_normalize(
        self, run_type: str, params: Dict[str, Any]
    ) -> ContextSnapshot:
        """Invoke a context surface and normalize into a snapshot."""
        response = self._invoke(run_type, params)
        return _normalize_context(response)

    # ── Lifecycle ───────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "ContextClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ──────────────────────────────────────────────────────────────
# Normalization helpers
# ──────────────────────────────────────────────────────────────

def _safe_str(d: Any, key: str) -> str:
    val = d.get(key) if isinstance(d, dict) else None
    return str(val) if val is not None else ""


def _safe_int(d: Any, key: str) -> int:
    val = d.get(key) if isinstance(d, dict) else None
    return int(val) if isinstance(val, int) else 0


def _safe_list(d: Any, key: str) -> List[Any]:
    val = d.get(key) if isinstance(d, dict) else None
    return list(val) if isinstance(val, list) else []


def _safe_dict(d: Any, key: str) -> Dict[str, Any]:
    val = d.get(key) if isinstance(d, dict) else None
    return dict(val) if isinstance(val, dict) else {}


def _normalize_context(response: RunStartResponse) -> ContextSnapshot:
    """Normalize a context.compile response into a ContextSnapshot.

    Extracts participant-relevant sections from the raw response
    data.  Tolerates missing sections gracefully.  Never fabricates
    missing context.
    """
    data = response.data
    raw = response.raw
    now = datetime.now(timezone.utc).isoformat()

    topology = _extract_topology(data)
    contracts = _extract_contracts(data)
    interfaces = _extract_interfaces(data)
    context_access = _extract_context_access(data)
    guidance = _extract_guidance(data)
    retrieval = _extract_retrieval_metadata(data, response.run_type, now)

    return ContextSnapshot(
        topology=topology,
        contracts=contracts,
        interfaces=interfaces,
        context_access=context_access,
        guidance=guidance,
        retrieval=retrieval,
        raw=raw,
    )


def _extract_topology(data: Dict[str, Any]) -> TopologyInfo:
    topo = _safe_dict(data, "topology")
    if not topo:
        topo = _safe_dict(data, "platform")
    return TopologyInfo(
        platform_name=_safe_str(topo, "platform_name") or _safe_str(topo, "name"),
        governance_model=_safe_str(topo, "governance_model") or _safe_str(topo, "model"),
        primary_surfaces=_safe_list(topo, "primary_surfaces") or _safe_list(topo, "surfaces"),
        runtime_model=_safe_str(topo, "runtime_model"),
        deployment_model=_safe_str(topo, "deployment_model"),
    )


def _extract_contracts(data: Dict[str, Any]) -> ContractInfo:
    ct = _safe_dict(data, "contracts")
    return ContractInfo(
        mcp_contract=_safe_str(ct, "mcp_contract") or _safe_str(ct, "contract"),
        envelope_schema=_safe_str(ct, "envelope_schema"),
        passport_schema=_safe_str(ct, "passport_schema"),
        event_schema=_safe_str(ct, "event_schema"),
        identity_model=_safe_str(ct, "identity_model"),
        charter_model=_safe_str(ct, "charter_model"),
        workspace_model=_safe_str(ct, "workspace_model"),
    )


def _extract_interfaces(data: Dict[str, Any]) -> InterfaceInfo:
    iface = _safe_dict(data, "interfaces")
    return InterfaceInfo(endpoints=iface)


def _extract_context_access(data: Dict[str, Any]) -> ContextAccessInfo:
    ca = _safe_dict(data, "context_access")
    return ContextAccessInfo(
        implemented_surfaces=_safe_list(ca, "implemented_surfaces") or _safe_list(ca, "surfaces"),
        declared_count=_safe_int(ca, "declared_count"),
        implemented_count=_safe_int(ca, "implemented_count"),
    )


def _extract_guidance(data: Dict[str, Any]) -> GuidanceInfo:
    g = _safe_dict(data, "guidance")
    return GuidanceInfo(
        run_type_discipline=_safe_str(g, "run_type_discipline") or _safe_str(g, "run_type_rule"),
        discovery_guidance=_safe_str(g, "discovery_guidance"),
        gap_workflow_guidance=_safe_str(g, "gap_workflow_guidance"),
        event_query_guidance=_safe_str(g, "event_query_guidance"),
    )


def _extract_retrieval_metadata(
    data: Dict[str, Any], run_type: str, retrieved_at: str
) -> RetrievalMetadata:
    meta = _safe_dict(data, "metadata")
    return RetrievalMetadata(
        run_type=run_type,
        retrieved_at=retrieved_at,
        generated_at=_safe_str(meta, "generated_at"),
        digest=_safe_str(meta, "digest"),
        ctx_ref_sha256=_safe_str(meta, "ctx_ref_sha256"),
        correlation_id=_safe_str(meta, "correlation_id"),
        server_time=_safe_str(meta, "server_time"),
    )
