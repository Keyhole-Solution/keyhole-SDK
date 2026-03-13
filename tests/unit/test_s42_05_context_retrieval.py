"""Tests for CE-V5-S42-05 — Governed Context Retrieval Bootstrap.

Validates all acceptance criteria and functional requirements:

AC-1: Developer kit can invoke current read-only context surfaces through MCP
AC-2: Context retrieval occurs without reading private platform internals
AC-3: Context responses can be normalized into a stable local representation
AC-4: Docs instruct agents to retrieve context before assumption-making
AC-5: Support exists for the currently implemented context-access run types
AC-6: Normalized context preserves useful participant-relevant metadata
AC-7: Usage examples demonstrate context retrieval before implementation

FR-1: Read-only context invocation
FR-2: Boundary-only context retrieval
FR-3: Stable local representation
FR-4: Current surface support
FR-5: Usage before assumption
FR-6: Metadata preservation
FR-7: Conservative failure behavior
FR-8: Minimal participant-facing complexity
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ── Imports under test ──────────────────────────────────────
from keyhole_sdk.context import (
    ContextClient,
    ContextSnapshot,
    TopologyInfo,
    ContractInfo,
    InterfaceInfo,
    ContextAccessInfo,
    GuidanceInfo,
    RetrievalMetadata,
    RunStartRequest,
    RunStartResponse,
)
from keyhole_sdk.context.client import CONTEXT_RUN_TYPES, RUNS_START_PATH
from keyhole_sdk.exceptions import (
    AuthenticationError,
    SchemaError,
    TransportError,
)

REPO = Path(__file__).resolve().parent.parent.parent


def _read(rel_path: str) -> str:
    return (REPO / rel_path).read_text()


# ──────────────────────────────────────────────────────────────
# Helpers — mock HTTP responses
# ──────────────────────────────────────────────────────────────

def _make_context_response(
    run_type: str = "context.compile",
    status_code: int = 200,
    data: Dict[str, Any] | None = None
) -> MagicMock:
    """Build a mock requests.Response for a context run."""
    if data is None:
        data = {
            "status": "completed",
            "data": {
                "topology": {
                    "platform_name": "keyhole",
                    "governance_model": "recursive",
                    "primary_surfaces": ["mcp", "event-spine"],
                    "runtime_model": "promotion-driven",
                    "deployment_model": "boundary-separated",
                },
                "contracts": {
                    "mcp_contract": "mcp/v1",
                    "envelope_schema": "v1",
                    "passport_schema": "v1",
                    "event_schema": "v1",
                    "identity_model": "oidc-pkce",
                    "charter_model": "required",
                    "workspace_model": "supported",
                },
                "interfaces": {
                    "capabilities": "/mcp/v1/capabilities",
                    "whoami": "/mcp/v1/whoami",
                    "runs": "/mcp/v1/runs/start",
                },
                "context_access": {
                    "implemented_surfaces": [
                        "context.compile",
                        "gaps.list",
                        "lineage.get.v0_1",
                        "convergence.status.v0_1",
                    ],
                    "declared_count": 4,
                    "implemented_count": 4,
                },
                "guidance": {
                    "run_type_discipline": "exact canonical keys only",
                    "discovery_guidance": "capabilities first",
                    "gap_workflow_guidance": "use gaps.list",
                    "event_query_guidance": "POST /mcp/v1/events/query",
                },
                "metadata": {
                    "generated_at": "2026-03-13T12:00:00Z",
                    "digest": "sha256:abc123",
                    "ctx_ref_sha256": "sha256:def456",
                    "correlation_id": "corr-001",
                    "server_time": "2026-03-13T12:00:00Z",
                },
            },
        }

    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.text = json.dumps(data)
    return mock


# ──────────────────────────────────────────────────────────────
# AC-1 / FR-1 — Read-only context invocation
# ──────────────────────────────────────────────────────────────

class TestContextInvocation:
    """AC-1: Developer kit can invoke current read-only context surfaces."""

    def test_compile_context_invokes_runs_start(self):
        """compile_context() POSTs to /mcp/v1/runs/start."""
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://boundary.example.com",
                token="test-token",
                session=session,
            )
            snapshot = client.compile_context()
            session.post.assert_called_once()
            call_args = session.post.call_args
            assert RUNS_START_PATH in call_args[0][0]
            body = call_args[1]["json"]
            assert body["run_type"] == "context.compile"
            client.close()

    def test_list_gaps_invokes_correct_run_type(self):
        mock_response = _make_context_response(run_type="gaps.list")
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            result = client.list_gaps()
            body = session.post.call_args[1]["json"]
            assert body["run_type"] == "gaps.list"
            assert isinstance(result, RunStartResponse)
            client.close()

    def test_get_lineage_passes_target(self):
        mock_response = _make_context_response(run_type="lineage.get.v0_1")
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            client.get_lineage("my-artifact")
            body = session.post.call_args[1]["json"]
            assert body["run_type"] == "lineage.get.v0_1"
            assert body["params"]["target"] == "my-artifact"
            client.close()

    def test_get_convergence_status(self):
        mock_response = _make_context_response(run_type="convergence.status.v0_1")
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            result = client.get_convergence_status()
            body = session.post.call_args[1]["json"]
            assert body["run_type"] == "convergence.status.v0_1"
            client.close()

    def test_generic_invoke_accepts_known_run_type(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            result = client.invoke("context.compile")
            assert isinstance(result, RunStartResponse)
            client.close()

    def test_generic_invoke_rejects_unknown_run_type(self):
        client = ContextClient(
            base_url="https://example.com", token="t"
        )
        with pytest.raises(ValueError, match="Unknown context-access run type"):
            client.invoke("context.fabricated.v99")
        client.close()


# ──────────────────────────────────────────────────────────────
# AC-2 / FR-2 — Boundary-only context retrieval
# ──────────────────────────────────────────────────────────────

class TestBoundaryOnly:
    """AC-2: Context retrieval occurs through boundary, not private source."""

    def test_client_uses_bearer_token(self):
        """Client sends Authorization: Bearer header."""
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="my-token", session=session
            )
            client.compile_context()
            assert session.headers.__setitem__.call_args_list[1] == \
                (("Authorization", "Bearer my-token"),)
            client.close()

    def test_no_file_system_access_in_client(self):
        """Context client source does not open local files for context."""
        source = _read("packages/python/keyhole-sdk/keyhole_sdk/context/client.py")
        assert "open(" not in source or "# open(" in source
        assert "read_text" not in source
        assert "platform_source" not in source.lower()

    def test_no_private_paths_in_client(self):
        """No private platform paths in context client."""
        source = _read("packages/python/keyhole-sdk/keyhole_sdk/context/client.py")
        assert "keyhole-system" not in source
        assert "keyhole-storage" not in source
        assert "controller-manager" not in source


# ──────────────────────────────────────────────────────────────
# AC-3 / FR-3 — Stable local representation
# ──────────────────────────────────────────────────────────────

class TestNormalization:
    """AC-3: Context responses normalize into stable local representation."""

    def test_compile_returns_context_snapshot(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert isinstance(snapshot, ContextSnapshot)
            assert isinstance(snapshot.topology, TopologyInfo)
            assert isinstance(snapshot.contracts, ContractInfo)
            assert isinstance(snapshot.interfaces, InterfaceInfo)
            assert isinstance(snapshot.context_access, ContextAccessInfo)
            assert isinstance(snapshot.guidance, GuidanceInfo)
            assert isinstance(snapshot.retrieval, RetrievalMetadata)
            client.close()

    def test_topology_fields_extracted(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.get_platform_name() == "keyhole"
            assert snapshot.get_governance_model() == "recursive"
            assert "mcp" in snapshot.topology.primary_surfaces
            client.close()

    def test_contract_fields_extracted(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.get_mcp_contract() == "mcp/v1"
            assert snapshot.contracts.envelope_schema == "v1"
            client.close()

    def test_context_access_surfaces_extracted(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            surfaces = snapshot.get_implemented_surfaces()
            assert "context.compile" in surfaces
            assert "gaps.list" in surfaces
            assert "lineage.get.v0_1" in surfaces
            assert "convergence.status.v0_1" in surfaces
            client.close()

    def test_raw_response_preserved(self):
        """Full raw response preserved for traceability."""
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.raw != {}
            assert "status" in snapshot.raw
            client.close()

    def test_empty_response_normalizes_safely(self):
        """Missing sections normalize to empty defaults, not errors."""
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"status": "completed", "data": {}}
        mock.text = "{}"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.get_platform_name() == ""
            assert snapshot.get_mcp_contract() == ""
            assert snapshot.get_implemented_surfaces() == []
            client.close()


# ──────────────────────────────────────────────────────────────
# AC-4 / FR-5 — Docs instruct agents to retrieve context first
# ──────────────────────────────────────────────────────────────

class TestAgentGuidance:
    """AC-4: Docs instruct agents to retrieve context before assumptions."""

    def test_copilot_instructions_context_first(self):
        content = _read(".github/copilot-instructions.md")
        assert "Retrieve governed context before making assumptions" in content
        assert "ContextClient" in content
        assert "compile_context" in content

    def test_agent_md_context_first(self):
        content = _read("docs/AGENT.md")
        assert "context before" in content.lower() or \
               "retrieve governed context" in content.lower()
        assert "ContextClient" in content

    def test_readme_context_retrieval(self):
        content = _read("README.md")
        assert "ContextClient" in content
        assert "compile_context" in content

    def test_copilot_lists_context_run_types(self):
        content = _read(".github/copilot-instructions.md")
        assert "context.compile" in content
        assert "gaps.list" in content
        assert "lineage.get.v0_1" in content
        assert "convergence.status.v0_1" in content


# ──────────────────────────────────────────────────────────────
# AC-5 / FR-4 — Support for currently implemented run types
# ──────────────────────────────────────────────────────────────

class TestCurrentSurfaceSupport:
    """AC-5: Support for currently implemented context-access run types."""

    def test_context_compile_supported(self):
        assert "context.compile" in CONTEXT_RUN_TYPES

    def test_gaps_list_supported(self):
        assert "gaps.list" in CONTEXT_RUN_TYPES

    def test_lineage_get_supported(self):
        assert "lineage.get.v0_1" in CONTEXT_RUN_TYPES

    def test_convergence_status_supported(self):
        assert "convergence.status.v0_1" in CONTEXT_RUN_TYPES

    def test_no_fabricated_run_types(self):
        """Only the 4 disclosed run types are supported."""
        assert len(CONTEXT_RUN_TYPES) == 4

    def test_client_has_compile_method(self):
        assert hasattr(ContextClient, "compile_context")

    def test_client_has_gaps_method(self):
        assert hasattr(ContextClient, "list_gaps")

    def test_client_has_lineage_method(self):
        assert hasattr(ContextClient, "get_lineage")

    def test_client_has_convergence_method(self):
        assert hasattr(ContextClient, "get_convergence_status")


# ──────────────────────────────────────────────────────────────
# AC-6 / FR-6 — Metadata preservation
# ──────────────────────────────────────────────────────────────

class TestMetadataPreservation:
    """AC-6: Normalized context preserves useful metadata."""

    def test_retrieval_metadata_populated(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.retrieval.run_type == "context.compile"
            assert snapshot.retrieval.retrieved_at != ""
            assert snapshot.retrieval.generated_at == "2026-03-13T12:00:00Z"
            assert snapshot.retrieval.digest == "sha256:abc123"
            assert snapshot.retrieval.ctx_ref_sha256 == "sha256:def456"
            assert snapshot.retrieval.correlation_id == "corr-001"
            client.close()

    def test_digest_accessor(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.get_digest() == "sha256:abc123"
            client.close()

    def test_correlation_id_accessor(self):
        mock_response = _make_context_response()
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock_response
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            snapshot = client.compile_context()
            assert snapshot.get_correlation_id() == "corr-001"
            client.close()


# ──────────────────────────────────────────────────────────────
# AC-7 — Usage examples demonstrate context retrieval
# ──────────────────────────────────────────────────────────────

class TestUsageExamples:
    """AC-7: Usage examples demonstrate context retrieval before work."""

    def test_example_file_exists(self):
        path = REPO / "examples" / "python-client" / "retrieve_context.py"
        assert path.exists()

    def test_example_shows_discovery_first(self):
        content = _read("examples/python-client/retrieve_context.py")
        cap_idx = content.find("CapabilitiesClient")
        ctx_idx = content.find("ContextClient")
        assert cap_idx != -1
        assert ctx_idx != -1
        assert cap_idx < ctx_idx, "Discovery must come before context retrieval"

    def test_example_shows_4_steps(self):
        content = _read("examples/python-client/retrieve_context.py")
        assert "Step 1" in content
        assert "Step 2" in content
        assert "Step 3" in content
        assert "Step 4" in content

    def test_example_uses_context_client(self):
        content = _read("examples/python-client/retrieve_context.py")
        assert "compile_context" in content

    def test_example_requires_token(self):
        content = _read("examples/python-client/retrieve_context.py")
        assert "KEYHOLE_MCP_TOKEN" in content


# ──────────────────────────────────────────────────────────────
# FR-7 — Conservative failure behavior
# ──────────────────────────────────────────────────────────────

class TestFailureBehavior:
    """FR-7: Failed context retrieval must fail clearly, not fabricate."""

    def test_transport_error_on_connection_failure(self):
        import requests as req
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.side_effect = req.ConnectionError("refused")
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(TransportError):
                client.compile_context()
            client.close()

    def test_transport_error_on_timeout(self):
        import requests as req
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.side_effect = req.Timeout("timed out")
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(TransportError):
                client.compile_context()
            client.close()

    def test_auth_error_on_401(self):
        mock = MagicMock()
        mock.status_code = 401
        mock.text = "Unauthorized"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="bad", session=session
            )
            with pytest.raises(AuthenticationError):
                client.compile_context()
            client.close()

    def test_auth_error_on_403(self):
        mock = MagicMock()
        mock.status_code = 403
        mock.text = "Forbidden"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(AuthenticationError):
                client.compile_context()
            client.close()

    def test_transport_error_on_500(self):
        mock = MagicMock()
        mock.status_code = 500
        mock.text = "Internal Server Error"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(TransportError):
                client.compile_context()
            client.close()

    def test_schema_error_on_invalid_json(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.side_effect = ValueError("invalid json")
        mock.text = "not json"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(SchemaError):
                client.compile_context()
            client.close()

    def test_schema_error_on_non_dict(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = [1, 2, 3]
        mock.text = "[1,2,3]"
        with patch("keyhole_sdk.context.client.requests.Session") as MockSession:
            session = MockSession.return_value
            session.post.return_value = mock
            client = ContextClient(
                base_url="https://example.com", token="t", session=session
            )
            with pytest.raises(SchemaError):
                client.compile_context()
            client.close()


# ──────────────────────────────────────────────────────────────
# FR-8 — Minimal participant-facing complexity
# ──────────────────────────────────────────────────────────────

class TestMinimalComplexity:
    """FR-8: First version is small and bootstrap-oriented."""

    def test_context_manager_support(self):
        """Client supports with-statement."""
        client = ContextClient(base_url="https://example.com", token="t")
        with client:
            pass  # just verifying context manager works

    def test_sdk_exports_context_client(self):
        from keyhole_sdk import ContextClient as C
        assert C is ContextClient

    def test_sdk_exports_context_snapshot(self):
        from keyhole_sdk import ContextSnapshot as S
        assert S is ContextSnapshot


# ──────────────────────────────────────────────────────────────
# Model structure tests
# ──────────────────────────────────────────────────────────────

class TestModels:
    """Context models are well-structured Pydantic models."""

    def test_context_snapshot_defaults(self):
        snapshot = ContextSnapshot()
        assert snapshot.topology.platform_name == ""
        assert snapshot.contracts.mcp_contract == ""
        assert snapshot.get_implemented_surfaces() == []
        assert snapshot.raw == {}

    def test_run_start_request_shape(self):
        req = RunStartRequest(run_type="context.compile", params={"key": "val"})
        assert req.run_type == "context.compile"
        assert req.params == {"key": "val"}

    def test_run_start_response_shape(self):
        resp = RunStartResponse(
            run_type="context.compile",
            status="completed",
            data={"topology": {}},
            raw={"status": "completed"},
        )
        assert resp.run_type == "context.compile"
        assert resp.status == "completed"

    def test_topology_info_fields(self):
        t = TopologyInfo(
            platform_name="keyhole",
            governance_model="recursive",
            primary_surfaces=["mcp"],
        )
        assert t.platform_name == "keyhole"
        assert t.governance_model == "recursive"

    def test_guidance_info_fields(self):
        g = GuidanceInfo(
            run_type_discipline="exact keys only",
            discovery_guidance="capabilities first",
        )
        assert g.run_type_discipline == "exact keys only"

    def test_retrieval_metadata_fields(self):
        m = RetrievalMetadata(
            run_type="context.compile",
            retrieved_at="2026-03-13T12:00:00Z",
            digest="sha256:abc",
            correlation_id="corr-001",
        )
        assert m.digest == "sha256:abc"


# ──────────────────────────────────────────────────────────────
# Cross-doc consistency
# ──────────────────────────────────────────────────────────────

class TestCrossDocConsistency:
    """Cross-document consistency for context retrieval."""

    def test_readme_references_context_client(self):
        content = _read("README.md")
        assert "ContextClient" in content

    def test_copilot_references_context_client(self):
        content = _read(".github/copilot-instructions.md")
        assert "ContextClient" in content

    def test_agent_md_references_context_client(self):
        content = _read("docs/AGENT.md")
        assert "ContextClient" in content

    def test_boundary_constitution_updates(self):
        content = _read("docs/boundary-constitution.md")
        assert "governed context retrieval" in content.lower()
        # Should be struck through as completed
        assert "~~governed context retrieval~~" in content

    def test_example_file_in_inventory(self):
        content = _read("docs/specs/developer_ecosystem/public_surface_inventory.yaml")
        assert "retrieve_context.py" in content

    def test_no_fabricated_surfaces_in_docs(self):
        """Docs should not mention undeclared context surfaces."""
        copilot = _read(".github/copilot-instructions.md")
        # These four should exist
        for surface in ["context.compile", "gaps.list",
                        "lineage.get.v0_1", "convergence.status.v0_1"]:
            assert surface in copilot
        # These should NOT
        assert "context.query" not in copilot
        assert "context.list" not in copilot
        assert "gaps.get" not in copilot
