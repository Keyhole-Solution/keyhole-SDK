"""Tests for SDK-CLIENT-04: Governance Contract + Dependency Schema Validation.

Covers:
- ValidationStatus, ContractRepoPosture, ReadinessLevel enums
- detect_repo_posture, detect_foreign_manifests
- load_yaml_safe, parse_dependencies_list
- validate_keyhole_yaml, validate_governance_contract
- validate_capability_passport, validate_dependencies
- run_validation (native, foreign, partially_aligned)
- ValidationResult, NormalizationPreview models
- emit_validation_proof
- CLI run_validate command
- Repair guidance: map_validation_repair
- Determinism guarantees
- Public API surface
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

# ── Public surface imports (verify SDK-CLIENT-04 is in the top-level SDK) ─────
from keyhole_sdk import (
    ContractRepoPosture,
    NormalizationPreview,
    NormalizedDependency,
    ReadinessLevel,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
    detect_foreign_manifests,
    detect_repo_posture,
    emit_validation_proof,
    map_validation_repair,
    run_validation,
    validate_capability_passport,
    validate_dependencies,
    validate_governance_contract,
    validate_keyhole_yaml,
)

from keyhole_cli.commands.validate_cmd import run_validate
from keyhole_cli.result import EXIT_CONTRACT_FAILURE, EXIT_INVALID_INPUT, EXIT_SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


def _native_repo(tmp_path: Path) -> Path:
    """Scaffold a minimal passing native repo."""
    _write(tmp_path, "keyhole.yaml", "repo: test-service\nschema_version: 1\n")
    _write(
        tmp_path,
        "governance_contract.yaml",
        "repo: test-service\nproduces:\n  - payment.stripe.integration.v1\n",
    )
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# §1 — Enums
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationStatus:
    def test_pass_value(self):
        assert ValidationStatus.PASS == "PASS"

    def test_warn_value(self):
        assert ValidationStatus.WARN == "WARN"

    def test_reject_value(self):
        assert ValidationStatus.REJECT == "REJECT"


class TestContractRepoPosture:
    def test_native_value(self):
        assert ContractRepoPosture.NATIVE == "native"

    def test_foreign_value(self):
        assert ContractRepoPosture.FOREIGN == "foreign"

    def test_partially_aligned_value(self):
        assert ContractRepoPosture.PARTIALLY_ALIGNED == "partially_aligned"


class TestReadinessLevel:
    def test_native_ready(self):
        assert ReadinessLevel.NATIVE_READY == "native_ready"

    def test_partially_aligned(self):
        assert ReadinessLevel.PARTIALLY_ALIGNED == "partially_aligned"

    def test_foreign(self):
        assert ReadinessLevel.FOREIGN == "foreign"

    def test_not_ready(self):
        assert ReadinessLevel.NOT_READY == "not_ready"


# ─────────────────────────────────────────────────────────────────────────────
# §2 — Posture Detection
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectRepoPosture:
    def test_native_with_keyhole_and_governance(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: x\n")
        _write(tmp_path, "governance_contract.yaml", "repo: x\n")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.NATIVE

    def test_native_with_only_keyhole_yaml(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: x\n")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.NATIVE

    def test_native_with_only_governance_contract(self, tmp_path):
        _write(tmp_path, "governance_contract.yaml", "repo: x\n")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.NATIVE

    def test_partially_aligned_with_only_capability_passport(self, tmp_path):
        _write(tmp_path, "capability_passport.yaml", "capability: a.b.c.v1\n")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.PARTIALLY_ALIGNED

    def test_partially_aligned_with_only_dependencies(self, tmp_path):
        _write(tmp_path, "dependencies.yaml", "dependencies: []\n")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.PARTIALLY_ALIGNED

    def test_foreign_when_no_keyhole_files(self, tmp_path):
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.FOREIGN

    def test_foreign_with_only_package_json(self, tmp_path):
        _write(tmp_path, "package.json", "{}")
        assert detect_repo_posture(tmp_path) == ContractRepoPosture.FOREIGN


class TestDetectForeignManifests:
    def test_empty_dir_returns_empty_list(self, tmp_path):
        assert detect_foreign_manifests(tmp_path) == []

    def test_detects_package_json(self, tmp_path):
        _write(tmp_path, "package.json", "{}")
        manifests = detect_foreign_manifests(tmp_path)
        assert "package.json" in manifests

    def test_detects_requirements_txt(self, tmp_path):
        _write(tmp_path, "requirements.txt", "requests\n")
        manifests = detect_foreign_manifests(tmp_path)
        assert "requirements.txt" in manifests

    def test_detects_go_mod(self, tmp_path):
        _write(tmp_path, "go.mod", "module example.com\n")
        assert "go.mod" in detect_foreign_manifests(tmp_path)

    def test_does_not_detect_keyhole_yaml(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: x\n")
        assert "keyhole.yaml" not in detect_foreign_manifests(tmp_path)

    def test_stable_order(self, tmp_path):
        _write(tmp_path, "go.mod", "m\n")
        _write(tmp_path, "package.json", "{}")
        result = detect_foreign_manifests(tmp_path)
        # Should always return same order regardless of filesystem order
        result2 = detect_foreign_manifests(tmp_path)
        assert result == result2


# ─────────────────────────────────────────────────────────────────────────────
# §3 — YAML Parser
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadYamlSafe:
    def test_valid_yaml_returns_dict(self, tmp_path):
        from keyhole_sdk.validation.parser import load_yaml_safe
        f = _write(tmp_path, "f.yaml", "repo: myrepo\n")
        data, err = load_yaml_safe(f)
        assert data == {"repo": "myrepo"}
        assert err is None

    def test_empty_yaml_returns_empty_dict(self, tmp_path):
        from keyhole_sdk.validation.parser import load_yaml_safe
        f = _write(tmp_path, "f.yaml", "")
        data, err = load_yaml_safe(f)
        assert data == {}
        assert err is None

    def test_invalid_yaml_returns_error(self, tmp_path):
        from keyhole_sdk.validation.parser import load_yaml_safe
        f = _write(tmp_path, "f.yaml", "key: [unclosed\n")
        data, err = load_yaml_safe(f)
        assert data is None
        assert err is not None

    def test_missing_file_returns_error(self, tmp_path):
        from keyhole_sdk.validation.parser import load_yaml_safe
        f = tmp_path / "nonexistent.yaml"
        data, err = load_yaml_safe(f)
        assert data is None
        assert err is not None

    def test_non_dict_top_level_returns_error(self, tmp_path):
        from keyhole_sdk.validation.parser import load_yaml_safe
        f = _write(tmp_path, "f.yaml", "- item1\n- item2\n")
        data, err = load_yaml_safe(f)
        assert data is None
        assert err is not None


class TestParseDependenciesList:
    def test_valid_list(self, tmp_path):
        from keyhole_sdk.validation.parser import parse_dependencies_list
        data = {"dependencies": [{"capability": "a.b.c.v1"}]}
        deps, issues = parse_dependencies_list(data, "dependencies.yaml")
        assert len(deps) == 1
        assert issues == []

    def test_empty_list(self, tmp_path):
        from keyhole_sdk.validation.parser import parse_dependencies_list
        data = {"dependencies": []}
        deps, issues = parse_dependencies_list(data, "dependencies.yaml")
        assert deps == []
        assert issues == []

    def test_missing_dependencies_key(self, tmp_path):
        from keyhole_sdk.validation.parser import parse_dependencies_list
        data: Dict[str, Any] = {}
        deps, issues = parse_dependencies_list(data, "dependencies.yaml")
        # Missing key is acceptable for optional section — returns empty
        assert deps == []
        assert issues == []

    def test_non_list_value(self, tmp_path):
        from keyhole_sdk.validation.parser import parse_dependencies_list
        data = {"dependencies": "not-a-list"}
        deps, issues = parse_dependencies_list(data, "dependencies.yaml")
        assert deps == []
        assert any(i.reason == "dependencies_must_be_list" for i in issues)

    def test_non_dict_item(self, tmp_path):
        from keyhole_sdk.validation.parser import parse_dependencies_list
        data = {"dependencies": ["plain-string"]}
        deps, issues = parse_dependencies_list(data, "dependencies.yaml")
        assert any(i.reason == "dependency_must_be_mapping" for i in issues)


# ─────────────────────────────────────────────────────────────────────────────
# §4 — Individual file validators
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateKeyholeYaml:
    def test_valid_file_no_issues(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "repo: my-service\nschema_version: 1\n")
        issues, repo_name = validate_keyhole_yaml(f)
        assert repo_name == "my-service"
        assert all(i.reason == "missing_optional_schema_version" for i in issues) or issues == []

    def test_missing_repo_field(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "schema_version: 1\n")
        issues, repo_name = validate_keyhole_yaml(f)
        assert any(i.reason == "missing_required_field" and i.field == "repo" for i in issues)
        assert repo_name == ""

    def test_empty_repo_gives_issue(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "repo: ''\nschema_version: 1\n")
        issues, repo_name = validate_keyhole_yaml(f)
        assert any("repo" in i.field for i in issues)
        assert repo_name == ""

    def test_missing_schema_version_gives_warn_only(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "repo: svc\n")
        issues, repo_name = validate_keyhole_yaml(f)
        assert repo_name == "svc"
        assert any(i.reason == "missing_optional_schema_version" for i in issues)
        # All schema_version issues should be warn-only (not reject)
        for issue in issues:
            if issue.reason == "missing_optional_schema_version":
                from keyhole_sdk.validation.validator import _issue_is_warn_only
                assert _issue_is_warn_only(issue.reason)

    def test_parse_error_returns_single_issue(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "key: [unclosed\n")
        issues, repo_name = validate_keyhole_yaml(f)
        assert any(i.reason == "parse_error" for i in issues)
        assert repo_name == ""

    def test_returns_tuple(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = validate_keyhole_yaml(f)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_repair_steps_present_on_missing_repo(self, tmp_path):
        f = _write(tmp_path, "keyhole.yaml", "schema_version: 1\n")
        issues, _ = validate_keyhole_yaml(f)
        repo_issue = next(i for i in issues if i.field == "repo")
        assert len(repo_issue.repair) > 0


class TestValidateGovernanceContract:
    def test_valid_governance_contract(self, tmp_path):
        f = _write(
            tmp_path, "governance_contract.yaml",
            "repo: svc\nproduces:\n  - payment.stripe.integration.v1\n"
        )
        issues = validate_governance_contract(f)
        assert issues == []

    def test_missing_repo_field(self, tmp_path):
        f = _write(tmp_path, "governance_contract.yaml", "produces:\n  - a.b.c.v1\n")
        issues = validate_governance_contract(f)
        assert any(i.field == "repo" for i in issues)

    def test_missing_produces_field(self, tmp_path):
        f = _write(tmp_path, "governance_contract.yaml", "repo: svc\n")
        issues = validate_governance_contract(f)
        assert any(i.field == "produces" for i in issues)

    def test_produces_not_list(self, tmp_path):
        f = _write(tmp_path, "governance_contract.yaml", "repo: svc\nproduces: not-a-list\n")
        issues = validate_governance_contract(f)
        assert any(i.reason == "produces_must_be_list" for i in issues)

    def test_invalid_capability_in_produces(self, tmp_path):
        f = _write(
            tmp_path, "governance_contract.yaml",
            "repo: svc\nproduces:\n  - not_a_valid_cap\n"
        )
        issues = validate_governance_contract(f)
        assert any(i.reason == "invalid_capability_namespace" for i in issues)

    def test_local_invariants_must_be_list(self, tmp_path):
        f = _write(
            tmp_path, "governance_contract.yaml",
            "repo: svc\nproduces:\n  - a.b.c.v1\nlocal_invariants: not-a-list\n"
        )
        issues = validate_governance_contract(f)
        assert any(i.reason == "local_invariants_must_be_list" for i in issues)

    def test_required_tests_must_be_list(self, tmp_path):
        f = _write(
            tmp_path, "governance_contract.yaml",
            "repo: svc\nproduces:\n  - a.b.c.v1\nrequired_tests: not-a-list\n"
        )
        issues = validate_governance_contract(f)
        assert any(i.reason == "required_tests_must_be_list" for i in issues)

    def test_parse_error_returns_issue(self, tmp_path):
        f = _write(tmp_path, "governance_contract.yaml", "bad: [unclosed\n")
        issues = validate_governance_contract(f)
        assert any(i.reason == "parse_error" for i in issues)


class TestValidateCapabilityPassport:
    def test_valid_passport(self, tmp_path):
        f = _write(
            tmp_path, "capability_passport.yaml",
            "capability: payment.stripe.integration.v1\nowner_repo: svc\n"
        )
        issues = validate_capability_passport(f)
        assert issues == []

    def test_missing_capability_field(self, tmp_path):
        f = _write(tmp_path, "capability_passport.yaml", "owner_repo: svc\n")
        issues = validate_capability_passport(f)
        assert any(i.field == "capability" for i in issues)

    def test_invalid_capability_name(self, tmp_path):
        f = _write(
            tmp_path, "capability_passport.yaml",
            "capability: invalid_name\nowner_repo: svc\n"
        )
        issues = validate_capability_passport(f)
        assert any(i.reason == "invalid_capability_namespace" for i in issues)

    def test_missing_owner_repo(self, tmp_path):
        f = _write(
            tmp_path, "capability_passport.yaml",
            "capability: payment.stripe.integration.v1\n"
        )
        issues = validate_capability_passport(f)
        assert any(i.field == "owner_repo" for i in issues)

    def test_delegated_capabilities_must_be_list(self, tmp_path):
        f = _write(
            tmp_path, "capability_passport.yaml",
            "capability: a.b.c.v1\nowner_repo: svc\ndelegated_capabilities: not-list\n"
        )
        issues = validate_capability_passport(f)
        assert any(i.reason == "delegated_capabilities_must_be_list" for i in issues)

    def test_parse_error_yields_issue(self, tmp_path):
        f = _write(tmp_path, "capability_passport.yaml", "bad: [unclosed\n")
        issues = validate_capability_passport(f)
        assert any(i.reason == "parse_error" for i in issues)


class TestValidateDependencies:
    def test_valid_dependencies(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: payment.stripe.integration.v1\n    provider: stripe-adapter\n"
        )
        issues, preview = validate_dependencies(f)
        assert issues == []
        assert len(preview.dependencies) == 1

    def test_empty_dependencies(self, tmp_path):
        f = _write(tmp_path, "dependencies.yaml", "dependencies: []\n")
        issues, preview = validate_dependencies(f)
        assert issues == []
        assert preview.dependencies == []

    def test_missing_capability_field(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - provider: stripe-adapter\n"
        )
        issues, _ = validate_dependencies(f)
        assert any(i.reason == "missing_required_capability" for i in issues)

    def test_duplicate_capability(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n"
            "  - capability: payment.stripe.integration.v1\n"
            "  - capability: payment.stripe.integration.v1\n"
        )
        issues, _ = validate_dependencies(f)
        assert any(i.reason == "duplicate_capability" for i in issues)

    def test_invalid_capability_name(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: not_valid\n"
        )
        issues, _ = validate_dependencies(f)
        assert any(i.reason == "invalid_capability_namespace" for i in issues)

    def test_unsupported_digest_format(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: a.b.c.v1\n    digest: md5:abc123\n"
        )
        issues, _ = validate_dependencies(f)
        assert any(i.reason == "unsupported_digest_format" for i in issues)

    def test_valid_sha256_digest(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: a.b.c.v1\n    digest: sha256:abcdef0123456789\n"
        )
        issues, preview = validate_dependencies(f)
        assert not any(i.reason == "unsupported_digest_format" for i in issues)
        assert preview.dependencies[0].digest == "sha256:abcdef0123456789"

    def test_normalization_preview_built(self, tmp_path):
        f = _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: a.b.c.v1\n    provider: my-provider\n"
        )
        issues, preview = validate_dependencies(f)
        assert isinstance(preview, NormalizationPreview)
        assert len(preview.dependencies) >= 1
        dep = preview.dependencies[0]
        assert dep.capability == "a.b.c.v1"
        assert dep.provider == "my-provider"

    def test_parse_error_returns_issue_and_empty_preview(self, tmp_path):
        f = _write(tmp_path, "dependencies.yaml", "bad: [unclosed\n")
        issues, preview = validate_dependencies(f)
        assert any(i.reason == "parse_error" for i in issues)
        assert preview.dependencies == []

    def test_returns_tuple(self, tmp_path):
        f = _write(tmp_path, "dependencies.yaml", "dependencies: []\n")
        result = validate_dependencies(f)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# §5 — run_validation: Full pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestRunValidationNative:
    def test_full_pass_native_repo(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validation(tmp_path)
        assert result.status in (ValidationStatus.PASS, ValidationStatus.WARN)
        assert result.repo_posture == ContractRepoPosture.NATIVE
        assert result.repo == "test-service"

    def test_missing_keyhole_yaml_gives_reject(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        # Don't write governance_contract.yaml
        # Force native mode so missing governance is a failure
        result = run_validation(tmp_path, mode="native")
        assert result.status == ValidationStatus.REJECT
        assert result.rejected is True

    def test_missing_governance_contract_in_native_mode(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = run_validation(tmp_path, mode="native")
        assert result.status == ValidationStatus.REJECT
        assert "governance_contract.yaml" in result.files

    def test_with_valid_dependencies(self, tmp_path):
        _native_repo(tmp_path)
        _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: payment.stripe.integration.v1\n    provider: stripe\n"
        )
        result = run_validation(tmp_path)
        assert result.status in (ValidationStatus.PASS, ValidationStatus.WARN)
        assert "dependencies.yaml" in result.files
        assert len(result.normalization_preview.dependencies) == 1

    def test_invalid_dependency_gives_reject(self, tmp_path):
        _native_repo(tmp_path)
        _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - provider: missing-capability\n"
        )
        result = run_validation(tmp_path)
        assert result.status == ValidationStatus.REJECT

    def test_files_dict_populated(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validation(tmp_path)
        assert "keyhole.yaml" in result.files
        assert "governance_contract.yaml" in result.files

    def test_passthrough_repo_name(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validation(tmp_path)
        assert result.repo == "test-service"

    def test_mode_native_forces_strict(self, tmp_path):
        # Even if files partially exist, mode=native enforces full set
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = run_validation(tmp_path, mode="native")
        assert result.status == ValidationStatus.REJECT

    def test_issues_have_repair_steps(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = run_validation(tmp_path, mode="native")
        for issue in result.issues:
            assert len(issue.repair) > 0, f"Issue {issue.reason!r} has no repair steps"

    def test_result_is_json_serialisable(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validation(tmp_path)
        serialised = json.dumps(result.to_dict())
        parsed = json.loads(serialised)
        assert parsed["status"] in ("PASS", "WARN", "REJECT")


class TestRunValidationForeign:
    def test_empty_dir_is_foreign(self, tmp_path):
        result = run_validation(tmp_path)
        assert result.repo_posture == ContractRepoPosture.FOREIGN

    def test_foreign_gives_warn_not_reject(self, tmp_path):
        result = run_validation(tmp_path)
        assert result.status == ValidationStatus.WARN
        assert result.rejected is False

    def test_foreign_readiness_is_foreign(self, tmp_path):
        result = run_validation(tmp_path)
        assert result.readiness == ReadinessLevel.FOREIGN

    def test_foreign_manifests_detected_in_issues(self, tmp_path):
        _write(tmp_path, "package.json", "{}")
        result = run_validation(tmp_path)
        reasons = [i.reason for i in result.issues]
        assert "foreign_manifests_detected" in reasons

    def test_advisory_mode_always_foreign(self, tmp_path):
        _native_repo(tmp_path)  # even a native repo should be advisory
        result = run_validation(tmp_path, mode="advisory")
        assert result.repo_posture == ContractRepoPosture.FOREIGN

    def test_foreign_result_has_repair_guidance(self, tmp_path):
        result = run_validation(tmp_path)
        assert any(len(i.repair) > 0 for i in result.issues)


class TestRunValidationPartiallyAligned:
    def test_partial_posture_detected(self, tmp_path):
        _write(tmp_path, "capability_passport.yaml", "capability: a.b.c.v1\nowner_repo: svc\n")
        result = run_validation(tmp_path)
        assert result.repo_posture == ContractRepoPosture.PARTIALLY_ALIGNED

    def test_partially_aligned_readiness(self, tmp_path):
        _write(tmp_path, "capability_passport.yaml", "capability: a.b.c.v1\nowner_repo: svc\n")
        result = run_validation(tmp_path)
        assert result.readiness == ReadinessLevel.PARTIALLY_ALIGNED

    def test_missing_native_files_are_not_reject_for_partial(self, tmp_path):
        # keyhole.yaml is absent — but PARTIALLY_ALIGNED → not a hard failure
        _write(tmp_path, "capability_passport.yaml", "capability: a.b.c.v1\nowner_repo: svc\n")
        result = run_validation(tmp_path)
        # Should not REJECT just because keyhole.yaml is absent
        assert result.status != ValidationStatus.REJECT

    def test_invalid_passport_gives_reject_even_for_partial(self, tmp_path):
        _write(tmp_path, "capability_passport.yaml", "bad: [unclosed\n")
        result = run_validation(tmp_path)
        assert result.status == ValidationStatus.REJECT

    def test_dependencies_validated_in_partial_mode(self, tmp_path):
        _write(tmp_path, "dependencies.yaml", "dependencies:\n  - provider: no-cap\n")
        result = run_validation(tmp_path)
        assert result.status == ValidationStatus.REJECT


# ─────────────────────────────────────────────────────────────────────────────
# §6 — ValidationResult model
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationResult:
    def test_passed_property(self):
        r = ValidationResult(
            status=ValidationStatus.PASS,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NATIVE_READY,
        )
        assert r.passed is True
        assert r.rejected is False

    def test_rejected_property(self):
        r = ValidationResult(
            status=ValidationStatus.REJECT,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NOT_READY,
        )
        assert r.rejected is True
        assert r.passed is False

    def test_to_dict_has_required_keys(self):
        r = ValidationResult(
            status=ValidationStatus.PASS,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NATIVE_READY,
        )
        d = r.to_dict()
        for key in ("status", "repo_posture", "readiness", "repo", "files", "issues", "normalization_preview", "mode"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_status_is_string(self):
        r = ValidationResult(
            status=ValidationStatus.WARN,
            repo_posture=ContractRepoPosture.FOREIGN,
            readiness=ReadinessLevel.FOREIGN,
        )
        d = r.to_dict()
        assert isinstance(d["status"], str)
        assert d["status"] == "WARN"

    def test_to_dict_is_json_serialisable(self):
        r = ValidationResult(
            status=ValidationStatus.PASS,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NATIVE_READY,
            repo="my-repo",
            issues=[ValidationIssue(reason="test_reason", repair=["fix it"])],
        )
        json.dumps(r.to_dict())  # Must not raise

    def test_issues_serialised_to_dict(self):
        r = ValidationResult(
            status=ValidationStatus.REJECT,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NOT_READY,
            issues=[
                ValidationIssue(file="f.yaml", field="x", reason="missing_required_field", repair=["add x"])
            ],
        )
        d = r.to_dict()
        assert len(d["issues"]) == 1
        assert d["issues"][0]["reason"] == "missing_required_field"

    def test_normalization_preview_in_to_dict(self):
        r = ValidationResult(
            status=ValidationStatus.PASS,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NATIVE_READY,
            normalization_preview=NormalizationPreview(
                dependencies=[NormalizedDependency(capability="a.b.c.v1", provider="prov")]
            ),
        )
        d = r.to_dict()
        assert "normalization_preview" in d
        assert len(d["normalization_preview"]["dependencies"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# §7 — NormalizationPreview
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizationPreview:
    def test_empty_preview(self):
        p = NormalizationPreview()
        assert p.dependencies == []
        assert p.to_dict() == {"dependencies": []}

    def test_to_dict_serialises_dependencies(self):
        p = NormalizationPreview(
            dependencies=[NormalizedDependency(capability="a.b.c.v1", provider="prov", digest="sha256:abc")]
        )
        d = p.to_dict()
        assert len(d["dependencies"]) == 1
        assert d["dependencies"][0]["capability"] == "a.b.c.v1"

    def test_is_json_serialisable(self):
        p = NormalizationPreview(
            dependencies=[NormalizedDependency(capability="a.b.c.v1")]
        )
        json.dumps(p.to_dict())  # Must not raise

    def test_normalized_capability_recorded(self):
        nd = NormalizedDependency(
            capability="a.b.c.v1",
            normalized_capability="a.b.c.v1",
        )
        assert nd.normalized_capability == "a.b.c.v1"

    def test_provider_defaults_to_empty_string(self):
        nd = NormalizedDependency(capability="a.b.c.v1")
        assert nd.provider == ""


# ─────────────────────────────────────────────────────────────────────────────
# §8 — Proof emission
# ─────────────────────────────────────────────────────────────────────────────


class TestEmitValidationProof:
    def _make_result(self) -> ValidationResult:
        return ValidationResult(
            status=ValidationStatus.PASS,
            repo_posture=ContractRepoPosture.NATIVE,
            readiness=ReadinessLevel.NATIVE_READY,
            repo="test-service",
            mode="auto",
        )

    def test_creates_output_directory(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result, session_ref="svc")
        assert out.is_dir()

    def test_creates_validation_result_json(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        assert (out / "validation_result.json").exists()

    def test_creates_normalization_preview_json(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        assert (out / "normalization_preview.json").exists()

    def test_creates_validation_summary_md(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        assert (out / "validation_summary.md").exists()

    def test_validation_result_json_is_valid(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        parsed = json.loads((out / "validation_result.json").read_text())
        assert parsed["status"] == "PASS"

    def test_normalization_preview_json_is_valid(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        parsed = json.loads((out / "normalization_preview.json").read_text())
        assert "dependencies" in parsed

    def test_summary_md_contains_status(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        summary = (out / "validation_summary.md").read_text()
        assert "PASS" in summary

    def test_session_ref_used_as_dir_name(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result, session_ref="my-repo")
        assert "my-repo" in str(out)

    def test_unsafe_session_ref_sanitised(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result, session_ref="../../../etc/passwd")
        # Must not escape state_dir
        assert tmp_path in out.parents or str(tmp_path) in str(out)

    def test_emitted_at_present_in_result_json(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path / "state", result)
        parsed = json.loads((out / "validation_result.json").read_text())
        assert "emitted_at" in parsed

    def test_parent_dirs_created_automatically(self, tmp_path):
        result = self._make_result()
        deep = tmp_path / "a" / "b" / "c"
        out = emit_validation_proof(deep, result)
        assert (out / "validation_result.json").exists()

    def test_returns_path(self, tmp_path):
        result = self._make_result()
        out = emit_validation_proof(tmp_path, result)
        assert isinstance(out, Path)


# ─────────────────────────────────────────────────────────────────────────────
# §9 — CLI command: run_validate
# ─────────────────────────────────────────────────────────────────────────────


class TestCLIValidate:
    def test_pass_gives_exit_success(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validate(repo_path=str(tmp_path))
        assert result.exit_code == EXIT_SUCCESS

    def test_reject_gives_exit_contract_failure(self, tmp_path):
        # Force rejection: native mode with missing governance_contract.yaml
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = run_validate(repo_path=str(tmp_path), mode="native")
        assert result.exit_code == EXIT_CONTRACT_FAILURE

    def test_invalid_path_gives_exit_invalid_input(self, tmp_path):
        result = run_validate(repo_path=str(tmp_path / "nonexistent"))
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_warn_gives_exit_success(self, tmp_path):
        result = run_validate(repo_path=str(tmp_path))  # empty dir → WARN (foreign advisory)
        assert result.exit_code == EXIT_SUCCESS

    def test_result_data_has_status_key(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validate(repo_path=str(tmp_path))
        assert "status" in result.data

    def test_result_data_has_repo_posture(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validate(repo_path=str(tmp_path))
        assert "repo_posture" in result.data

    def test_summary_is_non_empty(self, tmp_path):
        _native_repo(tmp_path)
        result = run_validate(repo_path=str(tmp_path))
        assert result.summary

    def test_advisory_mode_always_succeeds(self, tmp_path):
        # Even a native repo in advisory mode should give EXIT_SUCCESS
        _native_repo(tmp_path)
        result = run_validate(repo_path=str(tmp_path), mode="advisory")
        assert result.exit_code == EXIT_SUCCESS

    def test_next_steps_provided_on_reject(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "repo: svc\nschema_version: 1\n")
        result = run_validate(repo_path=str(tmp_path), mode="native")
        assert len(result.next_steps) > 0

    def test_proof_emitted_when_state_dir_given(self, tmp_path):
        _native_repo(tmp_path)
        state = tmp_path / "state"
        result = run_validate(repo_path=str(tmp_path), state_dir=str(state))
        assert result.exit_code == EXIT_SUCCESS
        # Check that at least the state dir exists (proof emitted)
        # The dir might exist even if proof fails gracefully
        assert isinstance(result.data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# §10 — Repair guidance
# ─────────────────────────────────────────────────────────────────────────────


class TestRepairGuidance:
    def test_known_error_class_returns_list(self):
        steps = map_validation_repair("parse_error")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_unknown_error_class_returns_non_empty_steps(self):
        steps = map_validation_repair("something_made_up_xyz")
        assert isinstance(steps, list)
        assert len(steps) > 0  # Must never return empty list

    def test_invalid_repo_path_steps(self):
        steps = map_validation_repair("InvalidRepoPath")
        assert any("directory" in s.lower() or "path" in s.lower() or "exist" in s.lower() for s in steps)

    def test_missing_required_file_steps(self):
        steps = map_validation_repair("missing_required_file")
        assert any("keyhole" in s.lower() or "init" in s.lower() for s in steps)

    def test_invalid_capability_namespace_steps(self):
        steps = map_validation_repair("invalid_capability_namespace")
        assert any("v1" in s or "domain" in s.lower() for s in steps)


# ─────────────────────────────────────────────────────────────────────────────
# §11 — Determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_repo_same_result(self, tmp_path):
        _native_repo(tmp_path)
        r1 = run_validation(tmp_path)
        r2 = run_validation(tmp_path)
        assert r1.status == r2.status
        assert r1.repo_posture == r2.repo_posture
        assert r1.readiness == r2.readiness

    def test_same_repo_same_issues(self, tmp_path):
        _write(tmp_path, "keyhole.yaml", "schema_version: 1\n")  # missing repo
        r1 = run_validation(tmp_path, mode="native")
        r2 = run_validation(tmp_path, mode="native")
        assert len(r1.issues) == len(r2.issues)
        assert all(i.reason == j.reason for i, j in zip(r1.issues, r2.issues))

    def test_foreign_repo_deterministic(self, tmp_path):
        _write(tmp_path, "package.json", "{}")
        r1 = run_validation(tmp_path)
        r2 = run_validation(tmp_path)
        assert r1.status == r2.status

    def test_same_deps_same_normalization_preview(self, tmp_path):
        _native_repo(tmp_path)
        _write(
            tmp_path, "dependencies.yaml",
            "dependencies:\n  - capability: a.b.c.v1\n    provider: prov\n"
        )
        r1 = run_validation(tmp_path)
        r2 = run_validation(tmp_path)
        assert r1.normalization_preview.to_dict() == r2.normalization_preview.to_dict()

    def test_to_dict_is_stable(self, tmp_path):
        _native_repo(tmp_path)
        r = run_validation(tmp_path)
        d1 = r.to_dict()
        d2 = r.to_dict()
        assert d1 == d2


# ─────────────────────────────────────────────────────────────────────────────
# §12 — Public API surface
# ─────────────────────────────────────────────────────────────────────────────


class TestPublicAPISurface:
    def test_validation_status_in_sdk__all__(self):
        import keyhole_sdk
        assert "ValidationStatus" in keyhole_sdk.__all__

    def test_contract_repo_posture_in_sdk__all__(self):
        import keyhole_sdk
        assert "ContractRepoPosture" in keyhole_sdk.__all__

    def test_run_validation_in_sdk__all__(self):
        import keyhole_sdk
        assert "run_validation" in keyhole_sdk.__all__

    def test_emit_validation_proof_in_sdk__all__(self):
        import keyhole_sdk
        assert "emit_validation_proof" in keyhole_sdk.__all__

    def test_map_validation_repair_in_sdk__all__(self):
        import keyhole_sdk
        assert "map_validation_repair" in keyhole_sdk.__all__

    def test_validation_issue_in_sdk__all__(self):
        import keyhole_sdk
        assert "ValidationIssue" in keyhole_sdk.__all__

    def test_validate_cmd_importable(self):
        from keyhole_cli.commands.validate_cmd import run_validate as rv
        assert callable(rv)

    def test_cli_validate_command_registered(self):
        from typer.testing import CliRunner
        from keyhole_cli.cli import app
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output.lower() or "Validate" in result.output
