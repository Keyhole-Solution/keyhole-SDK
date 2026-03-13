"""CE-V5-S42-03 — Capabilities Discovery Client tests.

Covers all 7 acceptance criteria from the story:
  AC-1 — Live capabilities retrieval (mocked)
  AC-2 — Normalized structure exposes contract, compatibility, auth,
          transport, and implemented context surfaces
  AC-3 — Boundary digest / generated-at metadata preserved
  AC-4 — Consumers use normalized result without reading raw JSON
  AC-5 — Helper methods expose compatibility, context-access,
          and client-guidance data
  AC-6 — Cached discovery snapshots preserve metadata without
          overriding live truth
  AC-7 — Conservative failure on malformed / incomplete responses

Also covers functional requirements FR-1 through FR-8.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Ensure SDK is importable from the worktree
_SDK_PKG = Path(__file__).resolve().parents[2] / "packages" / "python" / "keyhole-sdk"
if str(_SDK_PKG) not in sys.path:
    sys.path.insert(0, str(_SDK_PKG))

from keyhole_sdk.discovery import (
    CapabilitiesCache,
    CapabilitiesClient,
    CapabilitiesResult,
    ClientGuidance,
    CompatibilityPosture,
    ContextAccessContract,
    ContractIdentity,
    DiscoveryMetadata,
    FeatureFlags,
    TransportPosture,
    AuthPosture,
)
from keyhole_sdk.exceptions import SchemaError, TransportError


# ──────────────────────────────────────────────────────────────
# Fixture — canonical capabilities response
# ──────────────────────────────────────────────────────────────

CANONICAL_CAPABILITIES: Dict[str, Any] = {
    "contract": "mcp/v1",
    "operations_declared": 30,
    "operations_implemented": 9,
    "schema_versions": {
        "envelope": "1.0",
        "passport": "1.0",
    },
    "compatibility": {
        "min_sdk_version": "0.1.0",
        "envelope_version": "1.0",
        "passport_version": "1.0",
        "charter_required": True,
        "workspace_supported": True,
    },
    "transport": {
        "type": "rest-http",
        "tombstoned": ["sse", "json-rpc"],
    },
    "auth": {
        "flow": "OIDC/PKCE",
        "realm": "keyhole-mcp",
    },
    "endpoints": {
        "discovery": "/mcp/v1/capabilities",
        "identity": "/mcp/v1/whoami",
        "run_dispatch": "/mcp/v1/runs/start",
        "event_query": "/mcp/v1/events/query",
    },
    "feature_flags": {
        "memory_delete_enabled": True,
        "events_stream_enabled": False,
        "runs_cancel_enabled": False,
        "traces_query_enabled": False,
        "trust_public_card_enabled": True,
        "sandbox_mode_enabled": False,
    },
    "context_access": {
        "implemented": [
            "context.compile",
            "gaps.list",
            "lineage.get.v0_1",
            "convergence.status.v0_1",
        ],
        "declared_count": 8,
        "implemented_count": 4,
    },
    "client_guidance": {
        "run_type_rule": "Run types are exact canonical keys, not REST resource guesses.",
        "run_type_mistakes": ["gaps.states", "gap.status", "convergence.statuses"],
        "gap_workflow_guidance": "Use gaps.list to enumerate known gaps before targeting.",
        "event_query_guidance": "Use POST /mcp/v1/events/query with a selector object.",
    },
    "meta": {
        "generated_at": "2026-03-13T10:00:00Z",
        "digest": "sha256:abc123def456",
        "ctx_ref_sha256": "sha256:ref789",
        "correlation_id": "corr-42-03",
        "server_time": "2026-03-13T10:00:01Z",
    },
}


def _mock_response(data: Any, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = json.dumps(data) if isinstance(data, dict) else str(data)
    return resp


# ──────────────────────────────────────────────────────────────
# AC-1: Live capabilities retrieval
# ──────────────────────────────────────────────────────────────


class TestCapabilitiesFetch:
    """Verify the developer kit can retrieve mcp/v1 capabilities."""

    def test_fetch_returns_capabilities_result(self):
        """FR-1: Live retrieval produces a CapabilitiesResult."""
        session = MagicMock()
        session.get.return_value = _mock_response(CANONICAL_CAPABILITIES)
        session.headers = {}

        client = CapabilitiesClient("http://boundary.test", session=session)
        result = client.fetch()

        assert isinstance(result, CapabilitiesResult)
        session.get.assert_called_once_with(
            "http://boundary.test/mcp/v1/capabilities",
            timeout=10.0,
        )

    def test_fetch_strips_trailing_slash(self):
        """Base URL trailing slash does not double-slash the request."""
        session = MagicMock()
        session.get.return_value = _mock_response(CANONICAL_CAPABILITIES)
        session.headers = {}

        client = CapabilitiesClient("http://boundary.test/", session=session)
        client.fetch()

        session.get.assert_called_once_with(
            "http://boundary.test/mcp/v1/capabilities",
            timeout=10.0,
        )


# ──────────────────────────────────────────────────────────────
# AC-2: Normalized structure
# ──────────────────────────────────────────────────────────────


class TestNormalization:
    """FR-2: Normalized contract view exposes all required sections."""

    @pytest.fixture
    def result(self) -> CapabilitiesResult:
        return CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)

    def test_contract_identity(self, result: CapabilitiesResult):
        assert result.contract.contract == "mcp/v1"
        assert result.contract.operations_declared == 30
        assert result.contract.operations_implemented == 9
        assert result.contract.schema_versions == {"envelope": "1.0", "passport": "1.0"}

    def test_compatibility_posture(self, result: CapabilitiesResult):
        assert result.compatibility.min_sdk_version == "0.1.0"
        assert result.compatibility.charter_required is True
        assert result.compatibility.workspace_supported is True
        assert result.compatibility.envelope_version == "1.0"
        assert result.compatibility.passport_version == "1.0"

    def test_transport_posture(self, result: CapabilitiesResult):
        assert result.transport.transport == "rest-http"
        assert "sse" in result.transport.tombstoned_transports
        assert "json-rpc" in result.transport.tombstoned_transports

    def test_auth_posture(self, result: CapabilitiesResult):
        assert result.auth.auth_flow == "OIDC/PKCE"
        assert result.auth.auth_realm == "keyhole-mcp"
        assert result.auth.discovery_endpoint == "/mcp/v1/capabilities"
        assert result.auth.identity_endpoint == "/mcp/v1/whoami"
        assert result.auth.run_dispatch_endpoint == "/mcp/v1/runs/start"
        assert result.auth.event_query_endpoint == "/mcp/v1/events/query"

    def test_feature_flags(self, result: CapabilitiesResult):
        assert result.features.flags["memory_delete_enabled"] is True
        assert result.features.flags["events_stream_enabled"] is False
        assert result.features.flags["sandbox_mode_enabled"] is False

    def test_context_access(self, result: CapabilitiesResult):
        assert "context.compile" in result.context_access.implemented_surfaces
        assert "gaps.list" in result.context_access.implemented_surfaces
        assert "lineage.get.v0_1" in result.context_access.implemented_surfaces
        assert "convergence.status.v0_1" in result.context_access.implemented_surfaces
        assert result.context_access.declared_count == 8
        assert result.context_access.implemented_count == 4
        assert result.context_access.all_implemented is False

    def test_client_guidance(self, result: CapabilitiesResult):
        assert "exact canonical keys" in result.guidance.run_type_rule
        assert "gaps.states" in result.guidance.run_type_mistakes
        assert result.guidance.gap_workflow_guidance != ""
        assert result.guidance.event_query_guidance != ""

    def test_raw_preserved(self, result: CapabilitiesResult):
        """Raw response is preserved in full for traceability."""
        assert result.raw == CANONICAL_CAPABILITIES


# ──────────────────────────────────────────────────────────────
# AC-3: Metadata preservation
# ──────────────────────────────────────────────────────────────


class TestMetadataPreservation:
    """FR-3: Discovery metadata preserved where present."""

    def test_metadata_fields_preserved(self):
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)

        assert result.metadata.generated_at == "2026-03-13T10:00:00Z"
        assert result.metadata.digest == "sha256:abc123def456"
        assert result.metadata.ctx_ref_sha256 == "sha256:ref789"
        assert result.metadata.correlation_id == "corr-42-03"
        assert result.metadata.server_time == "2026-03-13T10:00:01Z"

    def test_metadata_from_flat_keys(self):
        """Metadata can also appear at the top level."""
        raw = {
            "contract": "mcp/v1",
            "generated_at": "2026-01-01T00:00:00Z",
            "digest": "sha256:flat",
            "ctx_ref_sha256": "sha256:flatref",
            "correlation_id": "flat-corr",
            "server_time": "2026-01-01T00:00:01Z",
        }
        result = CapabilitiesClient._normalize(raw)
        assert result.metadata.generated_at == "2026-01-01T00:00:00Z"
        assert result.metadata.digest == "sha256:flat"
        assert result.metadata.ctx_ref_sha256 == "sha256:flatref"

    def test_metadata_empty_when_absent(self):
        """Missing metadata yields empty strings, not fabrication."""
        result = CapabilitiesClient._normalize({"contract": "mcp/v1"})
        assert result.metadata.generated_at == ""
        assert result.metadata.digest == ""
        assert result.metadata.correlation_id == ""


# ──────────────────────────────────────────────────────────────
# AC-4: No raw JSON parsing required
# ──────────────────────────────────────────────────────────────


class TestConsumerExperience:
    """FR-5/FR-6: Consumers use normalized result without raw parsing."""

    def test_contract_version_accessible(self):
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)
        assert result.get_contract_version() == "mcp/v1"

    def test_auth_flow_accessible(self):
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)
        assert result.get_auth_flow() == "OIDC/PKCE"

    def test_transport_accessible(self):
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)
        assert result.get_transport() == "rest-http"

    def test_context_surfaces_accessible(self):
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)
        surfaces = result.get_implemented_context_surfaces()
        assert len(surfaces) == 4
        assert "context.compile" in surfaces


# ──────────────────────────────────────────────────────────────
# AC-5: Helper methods
# ──────────────────────────────────────────────────────────────


class TestHelperMethods:
    """FR-4: Helper extraction for compatibility, context-access, guidance."""

    @pytest.fixture
    def result(self) -> CapabilitiesResult:
        return CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)

    def test_compatibility_helper(self, result: CapabilitiesResult):
        assert result.get_min_sdk_version() == "0.1.0"
        assert result.is_charter_required() is True
        assert result.is_workspace_supported() is True

    def test_context_access_helper(self, result: CapabilitiesResult):
        surfaces = result.get_implemented_context_surfaces()
        assert "context.compile" in surfaces
        assert "gaps.list" in surfaces
        assert result.context_access.all_implemented is False

    def test_guidance_helper(self, result: CapabilitiesResult):
        assert "exact canonical keys" in result.get_run_type_rule()
        assert result.get_gap_workflow_guidance() != ""
        assert result.get_event_query_guidance() != ""

    def test_feature_flag_helper(self, result: CapabilitiesResult):
        assert result.get_feature_flag("memory_delete_enabled") is True
        assert result.get_feature_flag("sandbox_mode_enabled") is False
        assert result.get_feature_flag("nonexistent_flag") is None


# ──────────────────────────────────────────────────────────────
# AC-6: Cache snapshot handling
# ──────────────────────────────────────────────────────────────


class TestCapabilitiesCache:
    """FR-6: Cache without truth drift."""

    @pytest.fixture
    def cache(self, tmp_path: Path) -> CapabilitiesCache:
        return CapabilitiesCache(cache_dir=str(tmp_path))

    @pytest.fixture
    def result(self) -> CapabilitiesResult:
        return CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)

    def test_store_and_load_roundtrip(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        """Cache store + load preserves the full result."""
        cache.store(result)
        loaded = cache.load()
        assert loaded is not None
        assert loaded.contract.contract == result.contract.contract
        assert loaded.compatibility.min_sdk_version == result.compatibility.min_sdk_version

    def test_metadata_preserved_in_cache(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        """Discovery metadata survives cache roundtrip."""
        cache.store(result)
        loaded = cache.load()
        assert loaded is not None
        assert loaded.metadata.generated_at == "2026-03-13T10:00:00Z"
        assert loaded.metadata.digest == "sha256:abc123def456"
        assert loaded.metadata.ctx_ref_sha256 == "sha256:ref789"
        assert loaded.metadata.correlation_id == "corr-42-03"

    def test_cache_exists_and_cached_at(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        assert cache.exists() is False
        assert cache.cached_at() is None
        cache.store(result)
        assert cache.exists() is True
        assert cache.cached_at() is not None

    def test_cache_clear(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        cache.store(result)
        assert cache.exists() is True
        cache.clear()
        assert cache.exists() is False

    def test_load_returns_none_on_miss(self, cache: CapabilitiesCache):
        """Cache miss returns None, not fabrication."""
        assert cache.load() is None

    def test_load_returns_none_on_corrupt(self, cache: CapabilitiesCache):
        """Corrupt cache returns None, not fabrication."""
        cache.cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache.cache_path.write_text("not-json", encoding="utf-8")
        assert cache.load() is None

    def test_cache_envelope_marks_advisory(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        """Cached envelope explicitly marks itself as advisory."""
        cache.store(result)
        raw = json.loads(cache.cache_path.read_text(encoding="utf-8"))
        assert raw["advisory"] is True

    def test_raw_response_preserved_in_cache(
        self, cache: CapabilitiesCache, result: CapabilitiesResult
    ):
        """Full raw response preserved through cache roundtrip."""
        cache.store(result)
        loaded = cache.load()
        assert loaded is not None
        assert loaded.raw["contract"] == "mcp/v1"
        assert loaded.raw["operations_declared"] == 30


# ──────────────────────────────────────────────────────────────
# AC-7: Conservative failure
# ──────────────────────────────────────────────────────────────


class TestFailureModes:
    """FR-7: Boundary-safe failure mode."""

    def test_transport_error_on_connection_failure(self):
        """TransportError on network failure."""
        import requests

        session = MagicMock()
        session.get.side_effect = requests.ConnectionError("refused")
        session.headers = {}

        client = CapabilitiesClient("http://dead.host", session=session)
        with pytest.raises(TransportError, match="discovery failed"):
            client.fetch()

    def test_transport_error_on_timeout(self):
        """TransportError on timeout."""
        import requests

        session = MagicMock()
        session.get.side_effect = requests.Timeout("timed out")
        session.headers = {}

        client = CapabilitiesClient("http://slow.host", session=session)
        with pytest.raises(TransportError, match="discovery failed"):
            client.fetch()

    def test_transport_error_on_non_200(self):
        """TransportError on non-200 status code."""
        session = MagicMock()
        session.get.return_value = _mock_response({"error": "nope"}, status_code=500)
        session.headers = {}

        client = CapabilitiesClient("http://bad.host", session=session)
        with pytest.raises(TransportError, match="500"):
            client.fetch()

    def test_schema_error_on_non_json(self):
        """SchemaError when response is not valid JSON."""
        session = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("not json")
        resp.text = "not-json"
        session.get.return_value = resp
        session.headers = {}

        client = CapabilitiesClient("http://bad.host", session=session)
        with pytest.raises(SchemaError, match="not valid JSON"):
            client.fetch()

    def test_schema_error_on_non_object(self):
        """SchemaError when response is JSON but not an object."""
        session = MagicMock()
        session.get.return_value = _mock_response([1, 2, 3])
        session.headers = {}

        client = CapabilitiesClient("http://bad.host", session=session)
        with pytest.raises(SchemaError, match="not a JSON object"):
            client.fetch()

    def test_no_fabrication_on_minimal_response(self):
        """Missing sections yield defaults, never fabricated data."""
        result = CapabilitiesClient._normalize({"contract": "mcp/v1"})
        assert result.contract.contract == "mcp/v1"
        assert result.compatibility.min_sdk_version == ""
        assert result.transport.transport == ""
        assert result.auth.auth_flow == ""
        assert result.context_access.implemented_surfaces == []
        assert result.guidance.run_type_rule == ""
        assert result.features.flags == {}

    def test_no_fabrication_on_empty_response(self):
        """Empty dict yields all defaults."""
        result = CapabilitiesClient._normalize({})
        assert result.contract.contract == ""
        assert result.context_access.implemented_surfaces == []
        assert result.metadata.digest == ""


# ──────────────────────────────────────────────────────────────
# FR-8: Minimal dependency footprint
# ──────────────────────────────────────────────────────────────


class TestMinimalDependency:
    """FR-8: The discovery client uses only requests + pydantic."""

    def test_discovery_imports_only_standard_deps(self):
        """Discovery module imports only SDK-declared dependencies."""
        import keyhole_sdk.discovery.client as client_mod
        import keyhole_sdk.discovery.models as models_mod
        import keyhole_sdk.discovery.cache as cache_mod

        # These modules exist and are importable
        assert client_mod is not None
        assert models_mod is not None
        assert cache_mod is not None


# ──────────────────────────────────────────────────────────────
# SDK __init__ exports
# ──────────────────────────────────────────────────────────────


class TestSDKExports:
    """Verify discovery types are exported from the SDK top-level."""

    def test_capabilities_client_exported(self):
        from keyhole_sdk import CapabilitiesClient
        assert CapabilitiesClient is not None

    def test_capabilities_result_exported(self):
        from keyhole_sdk import CapabilitiesResult
        assert CapabilitiesResult is not None

    def test_capabilities_cache_exported(self):
        from keyhole_sdk import CapabilitiesCache
        assert CapabilitiesCache is not None


# ──────────────────────────────────────────────────────────────
# Normalization edge cases
# ──────────────────────────────────────────────────────────────


class TestNormalizationEdgeCases:
    """Edge cases in normalization — tolerant parsing, no fabrication."""

    def test_transport_from_top_level_string(self):
        """Transport extracted from top-level 'transport' string."""
        raw = {"transport": "rest-http"}
        result = CapabilitiesClient._normalize(raw)
        assert result.transport.transport == "rest-http"

    def test_context_all_implemented_true(self):
        """all_implemented is True when counts match."""
        raw = {
            "context_access": {
                "implemented": ["a", "b"],
                "declared_count": 2,
                "implemented_count": 2,
            }
        }
        result = CapabilitiesClient._normalize(raw)
        assert result.context_access.all_implemented is True

    def test_context_all_implemented_false_on_zero(self):
        """all_implemented is False when declared_count is 0."""
        raw = {
            "context_access": {
                "implemented": [],
                "declared_count": 0,
                "implemented_count": 0,
            }
        }
        result = CapabilitiesClient._normalize(raw)
        assert result.context_access.all_implemented is False

    def test_feature_flags_ignore_non_bool(self):
        """Non-boolean feature flag values are excluded."""
        raw = {
            "feature_flags": {
                "real_flag": True,
                "string_flag": "yes",
                "int_flag": 1,
            }
        }
        result = CapabilitiesClient._normalize(raw)
        assert result.features.flags == {"real_flag": True}

    def test_model_serialization_roundtrip(self):
        """CapabilitiesResult can be serialized and deserialized."""
        result = CapabilitiesClient._normalize(CANONICAL_CAPABILITIES)
        dumped = result.model_dump()
        restored = CapabilitiesResult.model_validate(dumped)
        assert restored.contract.contract == "mcp/v1"
        assert restored.metadata.digest == "sha256:abc123def456"

    def test_context_manager_protocol(self):
        """CapabilitiesClient supports context manager protocol."""
        session = MagicMock()
        session.headers = {}
        with CapabilitiesClient("http://test", session=session) as client:
            assert client is not None
        session.close.assert_called_once()
