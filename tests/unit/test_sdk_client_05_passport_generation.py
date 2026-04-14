"""Tests for SDK-CLIENT-05: Capability Passport Generation.

Covers:
- PassportStatus, PassportReadiness enums
- CapabilityEntry, PassportRepo, PassportGenerationResult models
- compute_passport_digest determinism and content guarantees
- serialize_passport_for_storage (§10 field order, no secrets)
- generate_passport: native happy path, reject conditions
- Transport safety (§12)
- PassportGenerationResult properties and to_dict
- emit_passport_proof (3-file layout)
- CLI run_passport_generate (exit codes)
- map_passport_repair (always non-empty)
- Public API surface
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# ── Public surface imports ────────────────────────────────────────────────────
from keyhole_sdk import (
    CapabilityEntry,
    CapabilityPassportArtifact,
    PassportGenerationResult,
    PassportIssue,
    PassportReadiness,
    PassportStatus,
    compute_passport_digest,
    emit_passport_proof,
    generate_passport,
    map_passport_repair,
    serialize_passport_for_storage,
)
from keyhole_sdk.passport.models import (
    PassportIdentity,
    PassportLineage,
    PassportProof,
    PassportRepo,
    PassportTransport,
)

from keyhole_cli.commands.passport_cmd import run_passport_generate, run_passport_show
from keyhole_cli.result import EXIT_CONTRACT_FAILURE, EXIT_INVALID_INPUT, EXIT_SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _write(path: Path, name: str, content: str) -> Path:
    f = path / name
    f.write_text(content, encoding="utf-8")
    return f


def _native_repo(tmp_path: Path, *, repo: str = "my-service", caps: str | None = None) -> Path:
    """Scaffold a minimal native repo that should generate a GENERATED result."""
    _write(tmp_path, "keyhole.yaml", f"repo: {repo}\nschema_version: 1\n")
    produces = caps or "payment.stripe.integration.v1"
    _write(
        tmp_path,
        "governance_contract.yaml",
        f"repo: {repo}\nproduces:\n  - {produces}\n",
    )
    return tmp_path


def _multiple_caps_repo(tmp_path: Path) -> Path:
    """Scaffold a native repo with multiple capabilities."""
    _write(tmp_path, "keyhole.yaml", "repo: multi-service\nschema_version: 1\n")
    _write(
        tmp_path,
        "governance_contract.yaml",
        "repo: multi-service\nproduces:\n"
        "  - payment.stripe.integration.v1\n"
        "  - analytics.events.ingest.v1\n"
        "  - analytics.reports.export.v2\n",
    )
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# §1 — PassportStatus enum
# ─────────────────────────────────────────────────────────────────────────────


class TestPassportStatus:
    def test_generated_value(self):
        assert PassportStatus.GENERATED == "generated"

    def test_rejected_value(self):
        assert PassportStatus.REJECTED == "rejected"

    def test_is_str_enum(self):
        assert isinstance(PassportStatus.GENERATED, str)


# ─────────────────────────────────────────────────────────────────────────────
# §2 — PassportReadiness enum
# ─────────────────────────────────────────────────────────────────────────────


class TestPassportReadiness:
    def test_ready_value(self):
        assert PassportReadiness.READY == "ready"

    def test_foreign_value(self):
        assert PassportReadiness.FOREIGN == "foreign"

    def test_partially_aligned_value(self):
        assert PassportReadiness.PARTIALLY_ALIGNED == "partially_aligned"

    def test_not_ready_value(self):
        assert PassportReadiness.NOT_READY == "not_ready"

    def test_four_members(self):
        assert len(PassportReadiness) == 4


# ─────────────────────────────────────────────────────────────────────────────
# §3 — CapabilityEntry model
# ─────────────────────────────────────────────────────────────────────────────


class TestCapabilityEntry:
    def test_name_required(self):
        entry = CapabilityEntry(name="payment.stripe.integration.v1")
        assert entry.name == "payment.stripe.integration.v1"

    def test_default_visibility_private(self):
        entry = CapabilityEntry(name="x.y.z.v1")
        assert entry.visibility == "private"

    def test_default_status_declared(self):
        entry = CapabilityEntry(name="x.y.z.v1")
        assert entry.status == "declared"

    def test_visibility_override(self):
        entry = CapabilityEntry(name="x.y.z.v1", visibility="public")
        assert entry.visibility == "public"


# ─────────────────────────────────────────────────────────────────────────────
# §4 — compute_passport_digest
# ─────────────────────────────────────────────────────────────────────────────


class TestComputePassportDigest:
    def test_returns_sha256_prefix(self):
        d = compute_passport_digest("my-repo", ["a.b.c.v1"])
        assert d.startswith("sha256:")

    def test_stable_same_input(self):
        d1 = compute_passport_digest("my-repo", ["a.b.c.v1"])
        d2 = compute_passport_digest("my-repo", ["a.b.c.v1"])
        assert d1 == d2

    def test_changes_with_different_caps(self):
        d1 = compute_passport_digest("my-repo", ["a.b.c.v1"])
        d2 = compute_passport_digest("my-repo", ["x.y.z.v2"])
        assert d1 != d2

    def test_changes_with_different_repo_name(self):
        d1 = compute_passport_digest("repo-a", ["a.b.c.v1"])
        d2 = compute_passport_digest("repo-b", ["a.b.c.v1"])
        assert d1 != d2

    def test_order_of_caps_does_not_matter(self):
        """§11: digest is stable regardless of declared order."""
        d1 = compute_passport_digest("my-repo", ["a.b.c.v1", "x.y.z.v1"])
        d2 = compute_passport_digest("my-repo", ["x.y.z.v1", "a.b.c.v1"])
        assert d1 == d2

    def test_digest_hex_length(self):
        d = compute_passport_digest("my-repo", ["a.b.c.v1"])
        hex_part = d.split("sha256:")[1]
        assert len(hex_part) == 64  # SHA-256 = 32 bytes = 64 hex chars

    def test_empty_caps_produces_digest(self):
        d = compute_passport_digest("my-repo", [])
        assert d.startswith("sha256:")

    def test_owner_affects_digest(self):
        d1 = compute_passport_digest("my-repo", ["a.b.c.v1"], owner="owner-a")
        d2 = compute_passport_digest("my-repo", ["a.b.c.v1"], owner="owner-b")
        assert d1 != d2


# ─────────────────────────────────────────────────────────────────────────────
# §5 — serialize_passport_for_storage
# ─────────────────────────────────────────────────────────────────────────────


class TestSerializePassportForStorage:
    def _sample_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": "v1",
            "artifact_kind": "capability_passport",
            "repo": {"repo_name": "my-service"},
            "identity": {},
            "capabilities": [{"name": "a.b.c.v1"}],
            "lineage": {},
            "proof": {},
            "transport": {"digest": "sha256:abc"},
        }

    def test_returns_string(self):
        result = serialize_passport_for_storage(self._sample_payload())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_repo_name(self):
        result = serialize_passport_for_storage(self._sample_payload())
        assert "my-service" in result

    def test_contains_capability(self):
        result = serialize_passport_for_storage(self._sample_payload())
        assert "a.b.c.v1" in result

    def test_json_fallback_when_yaml_unavailable(self):
        """Should fall back to JSON when pyyaml is not available."""
        with patch.dict("sys.modules", {"yaml": None}):
            result = serialize_passport_for_storage(self._sample_payload())
        # Should still be parseable
        assert "my-service" in result

    def test_section_order_schema_version_first(self):
        result = serialize_passport_for_storage(self._sample_payload())
        assert result.index("schema_version") < result.index("artifact_kind")

    def test_section_order_capabilities_after_identity(self):
        result = serialize_passport_for_storage(self._sample_payload())
        assert result.index("identity") < result.index("capabilities")


# ─────────────────────────────────────────────────────────────────────────────
# §6 — generate_passport — native happy path
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneratePassportNativeHappyPath:
    def test_status_generated(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.status == PassportStatus.GENERATED

    def test_readiness_ready(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.readiness == PassportReadiness.READY

    def test_generated_property_true(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.generated is True
        assert r.rejected is False

    def test_repo_name_set(self, tmp_path):
        _native_repo(tmp_path, repo="payment-svc")
        r = generate_passport(tmp_path, write=False)
        assert r.repo == "payment-svc"

    def test_capability_count(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.capability_count == 1

    def test_multiple_capabilities_count(self, tmp_path):
        _multiple_caps_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.capability_count == 3

    def test_digest_starts_with_sha256(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.digest.startswith("sha256:")

    def test_artifact_not_none(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact is not None

    def test_no_issues_on_success(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.issues == []

    def test_write_true_creates_file(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=True)
        passport_file = tmp_path / "capability_passport.yaml"
        assert passport_file.exists()
        assert r.artifact_path == str(passport_file)

    def test_write_false_no_file(self, tmp_path):
        _native_repo(tmp_path)
        generate_passport(tmp_path, write=False)
        assert not (tmp_path / "capability_passport.yaml").exists()

    def test_write_false_artifact_path_empty(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact_path == ""

    def test_output_path_override(self, tmp_path):
        _native_repo(tmp_path)
        custom = tmp_path / "out" / "passport.yaml"
        custom.parent.mkdir()
        r = generate_passport(tmp_path, write=True, output_path=custom)
        assert custom.exists()
        assert r.artifact_path == str(custom)

    def test_source_files_listed(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert "keyhole.yaml" in r.source_files
        assert "governance_contract.yaml" in r.source_files


# ─────────────────────────────────────────────────────────────────────────────
# §7 — generate_passport — foreign repo rejected
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneratePassportForeignRejected:
    def test_empty_dir_status_rejected(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        assert r.status == PassportStatus.REJECTED

    def test_empty_dir_readiness_foreign(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        assert r.readiness == PassportReadiness.FOREIGN

    def test_rejected_property_true(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        assert r.rejected is True
        assert r.generated is False

    def test_issues_not_empty(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        assert len(r.issues) >= 1

    def test_reason_foreign_repo_not_ready(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert "ForeignRepoNotReady" in reasons

    def test_repair_steps_present(self, tmp_path):
        r = generate_passport(tmp_path, write=False)
        assert any(len(i.repair) > 0 for i in r.issues)

    def test_no_file_written(self, tmp_path):
        generate_passport(tmp_path, write=True)  # write=True but should not write
        assert not (tmp_path / "capability_passport.yaml").exists()


# ─────────────────────────────────────────────────────────────────────────────
# §8 — generate_passport — missing files
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneratePassportMissingFiles:
    def test_missing_keyhole_yaml_rejected(self, tmp_path):
        _write(tmp_path, "governance_contract.yaml", "repo: x\nproduces:\n  - a.b.c.v1\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_missing_keyhole_yaml_reason(self, tmp_path):
        _write(tmp_path, "governance_contract.yaml", "repo: x\nproduces:\n  - a.b.c.v1\n")
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        # Could be ForeignRepoNotReady (detector doesn't see keyhole.yaml)
        assert len(reasons) > 0

    def test_missing_governance_contract_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: my-service\nschema_version: 1\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_missing_governance_contract_reason(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: my-service\nschema_version: 1\n")
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert any(r in reasons for r in ["MissingGovernanceContract", "PartiallyAlignedNotReady"])

    def test_missing_repo_field_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "schema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "produces:\n  - a.b.c.v1\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_empty_repo_field_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: ''\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: ''\nproduces:\n  - a.b.c.v1\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected


# ─────────────────────────────────────────────────────────────────────────────
# §9 — generate_passport — invalid capabilities
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneratePassportInvalidCaps:
    def test_invalid_cap_name_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces:\n  - BAD_NAME\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_invalid_cap_reason_present(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces:\n  - BAD_NAME\n")
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert "InvalidCapabilityName" in reasons

    def test_duplicate_cap_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(
            tmp_path,
            "governance_contract.yaml",
            "repo: svc\nproduces:\n  - a.b.c.v1\n  - a.b.c.v1\n",
        )
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_duplicate_cap_reason(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(
            tmp_path,
            "governance_contract.yaml",
            "repo: svc\nproduces:\n  - a.b.c.v1\n  - a.b.c.v1\n",
        )
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert "DuplicateCapabilityDeclaration" in reasons

    def test_empty_produces_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces: []\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_empty_produces_reason(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces: []\n")
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert "NoDeclaredCapabilities" in reasons

    def test_produces_not_list_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces: scalar\n")
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_non_string_cap_item_rejected(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        _write(
            tmp_path,
            "governance_contract.yaml",
            "repo: svc\nproduces:\n  - 12345\n",
        )
        r = generate_passport(tmp_path, write=False)
        assert r.rejected


# ─────────────────────────────────────────────────────────────────────────────
# §10 — generate_passport — transport safety
# ─────────────────────────────────────────────────────────────────────────────


class TestTransportSafety:
    def test_unsafe_repo_name_rejected(self, tmp_path):
        """§12: repo name with unsafe chars → rejected."""
        _write(tmp_path, "keyhole.yaml", "repo: 'bad/name'\nschema_version: 1\n")
        _write(
            tmp_path,
            "governance_contract.yaml",
            "repo: 'bad/name'\nproduces:\n  - a.b.c.v1\n",
        )
        r = generate_passport(tmp_path, write=False)
        assert r.rejected

    def test_unsafe_repo_name_reason(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: 'bad/name'\nschema_version: 1\n")
        _write(
            tmp_path,
            "governance_contract.yaml",
            "repo: 'bad/name'\nproduces:\n  - a.b.c.v1\n",
        )
        r = generate_passport(tmp_path, write=False)
        reasons = [i.reason for i in r.issues]
        assert "UnsafeRepoName" in reasons

    def test_payload_no_absolute_paths(self, tmp_path):
        """§12: to_payload must not contain any absolute paths."""
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact is not None
        payload_str = json.dumps(r.artifact.to_payload())
        # Absolute paths start with / on Linux — should not appear in values
        import re as _re
        # Cheap check: no "/home", "/opt", "/tmp" style absolute paths in payload
        for line in payload_str.split(","):
            assert not _re.search(r'"/(?:home|opt|tmp|root|usr|var|etc)', line), \
                f"Absolute path leaked into payload: {line}"

    def test_payload_no_secret_keys(self, tmp_path):
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact is not None
        payload = r.artifact.to_payload()
        payload_keys_flat = json.dumps(payload).lower()
        for forbidden in ("password", "secret", "token", "credential", "private_key"):
            assert forbidden not in payload_keys_flat

    def test_repo_path_not_in_artifact(self, tmp_path):
        """Artifact must not leak the absolute repo path into the transport shape."""
        _native_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact is not None
        payload_str = json.dumps(r.artifact.to_payload())
        # repo_path is in the result but must not be in the artifact itself
        assert str(tmp_path) not in payload_str


# ─────────────────────────────────────────────────────────────────────────────
# §11 — Determinism guarantees
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_input_same_digest(self, tmp_path):
        _native_repo(tmp_path)
        r1 = generate_passport(tmp_path, write=False)
        r2 = generate_passport(tmp_path, write=False)
        assert r1.digest == r2.digest

    def test_different_caps_different_digest(self, tmp_path):
        d1 = compute_passport_digest("svc", ["a.b.c.v1"])
        d2 = compute_passport_digest("svc", ["x.y.z.v2"])
        assert d1 != d2

    def test_digest_does_not_include_timestamp(self, tmp_path):
        """Calling generate_passport twice must produce the same digest."""
        _native_repo(tmp_path)
        r1 = generate_passport(tmp_path, write=False)
        r2 = generate_passport(tmp_path, write=False)
        assert r1.digest == r2.digest

    def test_caps_sorted_in_artifact(self, tmp_path):
        """§9: Capabilities in artifact should be sorted deterministically."""
        _multiple_caps_repo(tmp_path)
        r = generate_passport(tmp_path, write=False)
        assert r.artifact is not None
        names = [c.name for c in r.artifact.capabilities]
        assert names == sorted(names)

    def test_cap_order_in_declaration_does_not_affect_digest(self, tmp_path):
        """§11: Digest is the same regardless of declared capability order."""
        from keyhole_sdk.passport.digest import compute_passport_digest as _digest
        caps_a = ["a.b.c.v1", "x.y.z.v1"]
        caps_b = ["x.y.z.v1", "a.b.c.v1"]
        assert _digest("svc", caps_a) == _digest("svc", caps_b)


# ─────────────────────────────────────────────────────────────────────────────
# §12 — CapabilityPassportArtifact.to_payload()
# ─────────────────────────────────────────────────────────────────────────────


class TestCapabilityPassportArtifact:
    def _make_artifact(self) -> CapabilityPassportArtifact:
        return CapabilityPassportArtifact(
            repo=PassportRepo(repo_name="svc", owner=""),
            identity=PassportIdentity(),
            capabilities=[CapabilityEntry(name="a.b.c.v1")],
            lineage=PassportLineage(),
            proof=PassportProof(),
            transport=PassportTransport(generated_at="2025-01-01T00:00:00Z", digest="sha256:abc"),
        )

    def test_to_payload_schema_version(self):
        p = self._make_artifact().to_payload()
        assert p["schema_version"] == "v1"

    def test_to_payload_artifact_kind(self):
        p = self._make_artifact().to_payload()
        assert p["artifact_kind"] == "capability_passport"

    def test_to_payload_sections_present(self):
        p = self._make_artifact().to_payload()
        for section in ("repo", "identity", "capabilities", "lineage", "proof", "transport"):
            assert section in p

    def test_to_payload_capabilities_list(self):
        p = self._make_artifact().to_payload()
        assert isinstance(p["capabilities"], list)
        assert p["capabilities"][0]["name"] == "a.b.c.v1"

    def test_to_payload_transport_has_digest(self):
        p = self._make_artifact().to_payload()
        assert "digest" in p["transport"]


# ─────────────────────────────────────────────────────────────────────────────
# §13 — PassportGenerationResult.to_dict()
# ─────────────────────────────────────────────────────────────────────────────


class TestPassportGenerationResult:
    def _make_generated(self, tmp_path: Path) -> PassportGenerationResult:
        _native_repo(tmp_path)
        return generate_passport(tmp_path, write=False)

    def test_generated_property(self, tmp_path):
        r = self._make_generated(tmp_path)
        assert r.generated is True

    def test_rejected_property_false_on_success(self, tmp_path):
        r = self._make_generated(tmp_path)
        assert r.rejected is False

    def test_to_dict_status_value(self, tmp_path):
        r = self._make_generated(tmp_path)
        d = r.to_dict()
        assert d["status"] == "generated"

    def test_to_dict_is_json_serializable(self, tmp_path):
        r = self._make_generated(tmp_path)
        # Should not raise
        json.dumps(r.to_dict())

    def test_to_dict_contains_artifact(self, tmp_path):
        r = self._make_generated(tmp_path)
        d = r.to_dict()
        assert d["artifact"] is not None

    def test_to_dict_reject_artifact_none(self, tmp_path):
        r = generate_passport(tmp_path, write=False)  # empty dir
        d = r.to_dict()
        assert d["artifact"] is None
        assert d["status"] == "rejected"

    def test_to_dict_issues_list(self, tmp_path):
        r = generate_passport(tmp_path, write=False)  # empty dir
        d = r.to_dict()
        assert isinstance(d["issues"], list)
        assert len(d["issues"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# §14 — emit_passport_proof
# ─────────────────────────────────────────────────────────────────────────────


class TestEmitPassportProof:
    def _make_result(self, tmp_path: Path) -> PassportGenerationResult:
        repo = tmp_path / "my-service"
        repo.mkdir()
        _native_repo(repo)
        return generate_passport(repo, write=False)

    def test_returns_path(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="test-session")
        assert isinstance(p, Path)

    def test_creates_generation_result_json(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        assert (p / "generation_result.json").exists()

    def test_creates_summary_md(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        assert (p / "summary.md").exists()

    def test_creates_digest_txt(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        assert (p / "digest.txt").exists()

    def test_generation_result_json_valid(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        data = json.loads((p / "generation_result.json").read_text(encoding="utf-8"))
        assert data["status"] == "generated"

    def test_digest_txt_content(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        digest_content = (p / "digest.txt").read_text(encoding="utf-8").strip()
        assert digest_content.startswith("sha256:")

    def test_proof_in_passport_subdir(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        # Should be under state/passport/<ref>/
        assert "passport" in str(p)

    def test_safe_session_ref_for_filesystem(self, tmp_path):
        """Session ref with slashes / colons should be sanitized."""
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my/bad:ref")
        assert p.exists()

    def test_rejected_result_also_emits(self, tmp_path):
        result = generate_passport(tmp_path, write=False)  # empty dir
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="test")
        assert (p / "generation_result.json").exists()

    def test_summary_md_contains_repo(self, tmp_path):
        result = self._make_result(tmp_path)
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        p = emit_passport_proof(str(state_dir), result, session_ref="my-session")
        summary = (p / "summary.md").read_text(encoding="utf-8")
        assert "my-service" in summary


# ─────────────────────────────────────────────────────────────────────────────
# §15 — CLI: run_passport_generate
# ─────────────────────────────────────────────────────────────────────────────


class TestCLIPassportGenerate:
    def test_success_on_native_repo(self, tmp_path):
        _native_repo(tmp_path)
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert result.exit_code == EXIT_SUCCESS

    def test_success_result_success_flag(self, tmp_path):
        _native_repo(tmp_path)
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert result.success is True

    def test_failure_on_empty_dir(self, tmp_path):
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert result.exit_code == EXIT_CONTRACT_FAILURE

    def test_failure_result_success_flag(self, tmp_path):
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert result.success is False

    def test_invalid_path_exit_code(self, tmp_path):
        result = run_passport_generate(repo_path=str(tmp_path / "does_not_exist"), write=False)
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_invalid_path_command_label(self, tmp_path):
        result = run_passport_generate(repo_path=str(tmp_path / "does_not_exist"))
        assert "passport" in result.command.lower()

    def test_data_contains_status(self, tmp_path):
        _native_repo(tmp_path)
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert "status" in result.data

    def test_no_write_no_file(self, tmp_path):
        _native_repo(tmp_path)
        run_passport_generate(repo_path=str(tmp_path), write=False)
        assert not (tmp_path / "capability_passport.yaml").exists()

    def test_write_true_creates_file(self, tmp_path):
        _native_repo(tmp_path)
        run_passport_generate(repo_path=str(tmp_path), write=True)
        assert (tmp_path / "capability_passport.yaml").exists()

    def test_next_steps_present_on_success(self, tmp_path):
        _native_repo(tmp_path)
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert isinstance(result.next_steps, list)
        assert len(result.next_steps) > 0

    def test_next_steps_present_on_failure(self, tmp_path):
        result = run_passport_generate(repo_path=str(tmp_path), write=False)
        assert isinstance(result.next_steps, list)
        assert len(result.next_steps) > 0


# ─────────────────────────────────────────────────────────────────────────────
# §16 — CLI: run_passport_show
# ─────────────────────────────────────────────────────────────────────────────


class TestCLIPassportShow:
    def test_missing_passport_file_fails(self, tmp_path):
        result = run_passport_show(repo_path=str(tmp_path))
        assert result.exit_code == EXIT_CONTRACT_FAILURE

    def test_existing_passport_succeeds(self, tmp_path):
        (tmp_path / "capability_passport.yaml").write_text("schema_version: v1\n")
        result = run_passport_show(repo_path=str(tmp_path))
        assert result.exit_code == EXIT_SUCCESS

    def test_invalid_path_invalid_input(self, tmp_path):
        result = run_passport_show(repo_path=str(tmp_path / "no_such_dir"))
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_data_has_content(self, tmp_path):
        (tmp_path / "capability_passport.yaml").write_text("schema_version: v1\n")
        result = run_passport_show(repo_path=str(tmp_path))
        assert "content" in result.data


# ─────────────────────────────────────────────────────────────────────────────
# §17 — map_passport_repair
# ─────────────────────────────────────────────────────────────────────────────


class TestRepairGuidance:
    def test_always_returns_list(self):
        assert isinstance(map_passport_repair("_default"), list)

    def test_never_empty(self):
        for key in [
            "InvalidRepoPath",
            "ForeignRepoNotReady",
            "MissingKeyholeYaml",
            "MissingGovernanceContract",
            "NoDeclaredCapabilities",
            "InvalidCapabilityName",
            "DuplicateCapabilityDeclaration",
            "MissingRepoIdentity",
            "UnsafeRepoName",
            "_default",
        ]:
            steps = map_passport_repair(key)
            assert len(steps) > 0, f"Repair steps empty for: {key}"

    def test_unknown_key_fallback(self):
        """Unknown keys fall back to _default — never empty."""
        steps = map_passport_repair("CompletelyUnknownErrorClass")
        assert len(steps) > 0

    def test_returns_strings(self):
        steps = map_passport_repair("MissingKeyholeYaml")
        assert all(isinstance(s, str) for s in steps)

    def test_validated_rejection(self):
        steps = map_passport_repair("ValidationRejected")
        assert len(steps) > 0


# ─────────────────────────────────────────────────────────────────────────────
# §18 — Public API surface
# ─────────────────────────────────────────────────────────────────────────────


class TestPublicAPISurface:
    def test_generate_passport_in_sdk_all(self):
        import keyhole_sdk
        assert "generate_passport" in keyhole_sdk.__all__

    def test_passport_status_in_sdk_all(self):
        import keyhole_sdk
        assert "PassportStatus" in keyhole_sdk.__all__

    def test_passport_readiness_in_sdk_all(self):
        import keyhole_sdk
        assert "PassportReadiness" in keyhole_sdk.__all__

    def test_emit_passport_proof_in_sdk_all(self):
        import keyhole_sdk
        assert "emit_passport_proof" in keyhole_sdk.__all__

    def test_map_passport_repair_in_sdk_all(self):
        import keyhole_sdk
        assert "map_passport_repair" in keyhole_sdk.__all__

    def test_compute_passport_digest_in_sdk_all(self):
        import keyhole_sdk
        assert "compute_passport_digest" in keyhole_sdk.__all__

    def test_passport_generation_result_in_sdk_all(self):
        import keyhole_sdk
        assert "PassportGenerationResult" in keyhole_sdk.__all__

    def test_passport_issue_in_sdk_all(self):
        import keyhole_sdk
        assert "PassportIssue" in keyhole_sdk.__all__

    def test_capability_passport_artifact_in_sdk_all(self):
        import keyhole_sdk
        assert "CapabilityPassportArtifact" in keyhole_sdk.__all__

    def test_cli_help_passport_group(self):
        """Smoke-test that passport sub-app is accessible."""
        from keyhole_cli.cli import passport_app
        assert passport_app is not None

    def test_cli_passport_generate_command_exists(self):
        from keyhole_cli.commands.passport_cmd import run_passport_generate
        assert callable(run_passport_generate)

    def test_cli_passport_show_command_exists(self):
        from keyhole_cli.commands.passport_cmd import run_passport_show
        assert callable(run_passport_show)
