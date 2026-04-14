"""Governance contract and dependency schema validation — SDK-CLIENT-04.

§8: Client responsibilities — posture detection, file discovery, schema parsing,
    contract validation, dependency validation, passport validation,
    normalization preview, repair-oriented output.

§11.1: Deterministic — same repo contents + mode → same result.
§11.2: Local-first — no live MCP server required.
§11.3: Fail-closed — malformed data must not be silently treated as valid.
§11.4: Advisory honesty — missing Keyhole files in foreign repos are not hard failures.
§11.5: Preview, not authority — normalization is preview only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from keyhole_sdk.validation.detector import (
    ALL_KEYHOLE_FILES,
    NATIVE_SIGNALS,
    detect_foreign_manifests,
    detect_repo_posture,
)
from keyhole_sdk.validation.models import (
    ContractRepoPosture,
    NormalizedDependency,
    NormalizationPreview,
    ReadinessLevel,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from keyhole_sdk.validation.parser import load_yaml_safe, parse_dependencies_list


# ── Constants ─────────────────────────────────────────────────────────────────

# Min required fields for each canonical file
_KEYHOLE_YAML_REQUIRED = ("repo",)
_GOVERNANCE_CONTRACT_REQUIRED = ("repo", "produces")
_CAPABILITY_PASSPORT_REQUIRED = ("capability", "owner_repo")

# Digest prefix whitelist for §8.5 digest shape validation
_DIGEST_PREFIXES = ("sha256:", "sha512:", "sha384:")


# ── Individual file validators ────────────────────────────────────────────────


def validate_keyhole_yaml(path: Path) -> Tuple[List[ValidationIssue], str]:
    """§9.1 — Validate keyhole.yaml.

    Returns (issues, repo_name). repo_name is empty on parse error.
    """
    fname = path.name
    data, err = load_yaml_safe(path)
    if err:
        return [ValidationIssue(
            file=fname, reason="parse_error",
            repair=[f"Fix the YAML syntax in {fname}.", err],
        )], ""

    issues: List[ValidationIssue] = []
    repo_name = ""

    # Required: repo
    if "repo" not in data:
        issues.append(ValidationIssue(
            file=fname, field="repo",
            reason="missing_required_field",
            repair=[f"Add a 'repo' field to {fname}: repo: my-repo-name"],
        ))
    else:
        rn = data["repo"]
        if not isinstance(rn, str) or not rn.strip():
            issues.append(ValidationIssue(
                file=fname, field="repo",
                reason="empty_or_invalid_repo_name",
                repair=["The 'repo' field must be a non-empty string."],
            ))
        else:
            repo_name = rn.strip()

    # Optional but recommended: schema_version
    if "schema_version" not in data:
        issues.append(ValidationIssue(
            file=fname, field="schema_version",
            reason="missing_optional_schema_version",
            repair=[f"Add 'schema_version: 1' to {fname} for future compatibility."],
        ))

    return issues, repo_name


def validate_governance_contract(path: Path) -> List[ValidationIssue]:
    """§9.2 — Validate governance_contract.yaml.

    Required top-level keys: repo, produces.
    Optional: parent_repo, required_tests, local_invariants, compatibility_contracts.
    """
    fname = path.name
    data, err = load_yaml_safe(path)
    if err:
        return [ValidationIssue(
            file=fname, reason="parse_error",
            repair=[f"Fix the YAML syntax in {fname}.", err],
        )]

    issues: List[ValidationIssue] = []

    for key in _GOVERNANCE_CONTRACT_REQUIRED:
        if key not in data:
            issues.append(ValidationIssue(
                file=fname, field=key,
                reason="missing_required_field",
                repair=[f"Add the '{key}' field to {fname}."],
            ))

    # Validate produces list shape
    if "produces" in data:
        produces = data["produces"]
        if not isinstance(produces, list):
            issues.append(ValidationIssue(
                file=fname, field="produces",
                reason="produces_must_be_list",
                repair=["'produces' must be a YAML list of capability names."],
            ))
        else:
            for idx, cap in enumerate(produces):
                if not isinstance(cap, str):
                    issues.append(ValidationIssue(
                        file=fname, field=f"produces[{idx}]",
                        reason="produces_item_must_be_string",
                        repair=[f"produces[{idx}] must be a string capability name."],
                    ))
                else:
                    cap_issues = _validate_capability_name_field(fname, f"produces[{idx}]", cap)
                    issues.extend(cap_issues)

    # Validate local_invariants shape if present
    if "local_invariants" in data:
        inv = data["local_invariants"]
        if not isinstance(inv, list):
            issues.append(ValidationIssue(
                file=fname, field="local_invariants",
                reason="local_invariants_must_be_list",
                repair=["'local_invariants' must be a YAML list."],
            ))

    # Validate required_tests shape if present
    if "required_tests" in data:
        rt = data["required_tests"]
        if not isinstance(rt, list):
            issues.append(ValidationIssue(
                file=fname, field="required_tests",
                reason="required_tests_must_be_list",
                repair=["'required_tests' must be a YAML list."],
            ))

    return issues


def validate_capability_passport(path: Path) -> List[ValidationIssue]:
    """§9.3, §8.6 — Validate capability_passport.yaml for local structural correctness.

    Does not finalize trust or server lineage semantics.
    """
    fname = path.name
    data, err = load_yaml_safe(path)
    if err:
        return [ValidationIssue(
            file=fname, reason="parse_error",
            repair=[f"Fix the YAML syntax in {fname}.", err],
        )]

    issues: List[ValidationIssue] = []

    for key in _CAPABILITY_PASSPORT_REQUIRED:
        if key not in data:
            issues.append(ValidationIssue(
                file=fname, field=key,
                reason="missing_required_field",
                repair=[f"Add the '{key}' field to {fname}."],
            ))

    # Validate capability identifier with canonical namespace rules
    if "capability" in data:
        cap = data["capability"]
        if isinstance(cap, str):
            cap_issues = _validate_capability_name_field(fname, "capability", cap)
            issues.extend(cap_issues)
        else:
            issues.append(ValidationIssue(
                file=fname, field="capability",
                reason="capability_must_be_string",
                repair=["'capability' must be a canonical capability name string."],
            ))

    # Validate delegated_capabilities list shape
    if "delegated_capabilities" in data:
        dc = data["delegated_capabilities"]
        if not isinstance(dc, list):
            issues.append(ValidationIssue(
                file=fname, field="delegated_capabilities",
                reason="delegated_capabilities_must_be_list",
                repair=["'delegated_capabilities' must be a YAML list of strings."],
            ))
        else:
            for idx, cap in enumerate(dc):
                if not isinstance(cap, str):
                    issues.append(ValidationIssue(
                        file=fname, field=f"delegated_capabilities[{idx}]",
                        reason="delegated_capability_must_be_string",
                        repair=[f"delegated_capabilities[{idx}] must be a string."],
                    ))

    return issues


def validate_dependencies(path: Path) -> Tuple[List[ValidationIssue], NormalizationPreview]:
    """§9.4, §8.5 — Validate dependencies.yaml and build normalization preview.

    Returns (issues, normalization_preview).
    """
    fname = path.name
    data, err = load_yaml_safe(path)
    if err:
        return [ValidationIssue(
            file=fname, reason="parse_error",
            repair=[f"Fix the YAML syntax in {fname}.", err],
        )], NormalizationPreview()

    raw_deps, list_issues = parse_dependencies_list(data, fname)
    issues: List[ValidationIssue] = list(list_issues)
    normalized: List[NormalizedDependency] = []
    seen_capabilities: set = set()

    for idx, dep in enumerate(raw_deps):
        field_prefix = f"dependencies[{idx}]"

        # Required: capability
        cap = dep.get("capability", "")
        if not cap:
            issues.append(ValidationIssue(
                file=fname, field=f"{field_prefix}.capability",
                reason="missing_required_capability",
                repair=[
                    f"Add a 'capability' field to {field_prefix}.",
                    "Example: capability: payment.stripe.integration.v1",
                ],
            ))
            continue

        if not isinstance(cap, str):
            issues.append(ValidationIssue(
                file=fname, field=f"{field_prefix}.capability",
                reason="capability_must_be_string",
                repair=[f"{field_prefix}.capability must be a string."],
            ))
            continue

        # §8.5 — validate canonical capability name format
        cap_issues = _validate_capability_name_field(fname, f"{field_prefix}.capability", cap)
        issues.extend(cap_issues)

        # §8.5 — duplicate detection
        if cap in seen_capabilities:
            issues.append(ValidationIssue(
                file=fname, field=f"{field_prefix}.capability",
                reason="duplicate_capability",
                repair=[
                    f"Capability '{cap}' is declared more than once in {fname}.",
                    "Remove the duplicate entry.",
                ],
            ))
        else:
            seen_capabilities.add(cap)

        # Optional: provider
        provider = dep.get("provider", "")
        if provider and not isinstance(provider, str):
            issues.append(ValidationIssue(
                file=fname, field=f"{field_prefix}.provider",
                reason="provider_must_be_string",
                repair=[f"{field_prefix}.provider must be a string."],
            ))
            provider = ""

        # Optional: digest — §8.5 digest shape
        digest = dep.get("digest", "")
        if digest:
            if not isinstance(digest, str):
                issues.append(ValidationIssue(
                    file=fname, field=f"{field_prefix}.digest",
                    reason="digest_must_be_string",
                    repair=[f"{field_prefix}.digest must be a string prefixed with sha256:, sha512:, etc."],
                ))
                digest = ""
            elif not any(digest.startswith(p) for p in _DIGEST_PREFIXES):
                issues.append(ValidationIssue(
                    file=fname, field=f"{field_prefix}.digest",
                    reason="unsupported_digest_format",
                    repair=[
                        f"{field_prefix}.digest must begin with sha256:, sha512:, or sha384:.",
                        f"Got: '{digest[:40]}...' — recompute or remove the digest.",
                    ],
                ))
                digest = ""

        # §8.7 — normalization preview (§11.5: preview only, not authority)
        from keyhole_sdk.capability.namespace import validate_capability_name
        cap_result = validate_capability_name(cap)
        normalized.append(NormalizedDependency(
            capability=cap,
            provider=str(provider),
            digest=str(digest),
            normalized_capability=cap_result.normalized if cap_result.valid else "",
        ))

    return issues, NormalizationPreview(dependencies=normalized)


# ── Full validation pipeline ──────────────────────────────────────────────────


def run_validation(
    repo_path: Path,
    mode: str = "auto",
) -> ValidationResult:
    """§8 — Run the full validation pipeline for a repo.

    §11.1: Deterministic — same inputs → same result.
    §11.2: Local-first — no live MCP server needed.
    §11.4: Advisory honesty for foreign repos.

    Args:
        repo_path: Resolved path to the repo root.
        mode:  "auto" | "native" | "advisory".
    """
    # ── Determine posture ──────────────────────────────────────────────────
    if mode == "native":
        posture = ContractRepoPosture.NATIVE
    elif mode == "advisory":
        posture = ContractRepoPosture.FOREIGN
    else:
        posture = detect_repo_posture(repo_path)

    repo_name = repo_path.name

    # ── Foreign repo path — advisory only §11.4 ─────────────────────────────
    if posture == ContractRepoPosture.FOREIGN:
        return _build_foreign_result(repo_path, repo_name, mode)

    # ── Native / partially-aligned path ─────────────────────────────────────
    all_issues: List[ValidationIssue] = []
    file_statuses: Dict[str, str] = {}
    norm_preview = NormalizationPreview()

    # keyhole.yaml
    repo_name_holder = [repo_name]
    _validate_present_or_required(
        repo_path, "keyhole.yaml",
        required_for_native=(posture == ContractRepoPosture.NATIVE),
        all_issues=all_issues,
        file_statuses=file_statuses,
        repo_name_holder=repo_name_holder,
        validator_fn=_run_keyhole_yaml,
    )
    # Extract repo name from holder if keyhole.yaml was parsed successfully
    repo_name = repo_name_holder[0] or repo_name

    # governance_contract.yaml
    _validate_present_or_required(
        repo_path, "governance_contract.yaml",
        required_for_native=(posture == ContractRepoPosture.NATIVE),
        all_issues=all_issues,
        file_statuses=file_statuses,
        validator_fn=_run_governance_contract,
    )

    # capability_passport.yaml — optional always
    kf = repo_path / "capability_passport.yaml"
    if kf.exists():
        passport_issues = validate_capability_passport(kf)
        _record_file_result("capability_passport.yaml", passport_issues, all_issues, file_statuses)

    # dependencies.yaml — optional; builds norm preview
    df = repo_path / "dependencies.yaml"
    if df.exists():
        dep_issues, dep_preview = validate_dependencies(df)
        _record_file_result("dependencies.yaml", dep_issues, all_issues, file_statuses)
        norm_preview = dep_preview

    # Extract repo name if we found it in keyhole.yaml
    # (already extracted above via repo_name_holder)

    # ── Compute overall status ────────────────────────────────────────────────
    has_reject = any(s == ValidationStatus.REJECT.value for s in file_statuses.values())
    has_reject |= any(
        i.reason not in ("missing_optional_schema_version",)
        and _issue_is_warn_only(i.reason) is False
        and i.reason.startswith("missing_required")
        for i in all_issues
    )
    # Re-check: any REJECT file → overall REJECT
    has_reject = ValidationStatus.REJECT.value in file_statuses.values() or any(
        not _issue_is_warn_only(i.reason) for i in all_issues
    )
    has_warn = ValidationStatus.WARN.value in file_statuses.values() or any(
        _issue_is_warn_only(i.reason) for i in all_issues
    )

    if has_reject:
        overall = ValidationStatus.REJECT
    elif has_warn:
        overall = ValidationStatus.WARN
    else:
        overall = ValidationStatus.PASS

    # ── Compute readiness ─────────────────────────────────────────────────────
    if posture == ContractRepoPosture.PARTIALLY_ALIGNED:
        readiness = ReadinessLevel.PARTIALLY_ALIGNED
    elif overall == ValidationStatus.PASS:
        readiness = ReadinessLevel.NATIVE_READY
    else:
        readiness = ReadinessLevel.NOT_READY

    return ValidationResult(
        status=overall,
        repo_posture=posture,
        readiness=readiness,
        repo=repo_name,
        files=file_statuses,
        issues=all_issues,
        normalization_preview=norm_preview,
        mode=mode,
        repo_path=str(repo_path),
    )


# ── Private helpers ───────────────────────────────────────────────────────────


def _build_foreign_result(
    repo_path: Path,
    repo_name: str,
    mode: str,
) -> ValidationResult:
    """§11.4 — Honest advisory result for foreign repos.

    Missing native Keyhole files are NOT treated as hard failures.
    """
    manifests = detect_foreign_manifests(repo_path)
    issues: List[ValidationIssue] = []

    issues.append(ValidationIssue(
        file="",
        reason="native_governance_files_absent",
        repair=[
            "This repo has no Keyhole governance files.",
            "Run: keyhole ingest . — to begin alignment.",
            "Review alignment guidance before native registration.",
        ],
    ))

    if manifests:
        issues.append(ValidationIssue(
            file="",
            reason="foreign_manifests_detected",
            repair=[
                f"Detected dependency manifests: {', '.join(manifests)}.",
                "These can be used during ingestion to infer capabilities.",
            ],
        ))

    return ValidationResult(
        status=ValidationStatus.WARN,
        repo_posture=ContractRepoPosture.FOREIGN,
        readiness=ReadinessLevel.FOREIGN,
        repo=repo_name,
        files={},
        issues=issues,
        mode=mode,
        repo_path=str(repo_path),
    )


def _validate_present_or_required(
    repo_path: Path,
    fname: str,
    *,
    required_for_native: bool,
    all_issues: List[ValidationIssue],
    file_statuses: Dict[str, str],
    repo_name_holder: list | None = None,
    validator_fn=None,
) -> None:
    fpath = repo_path / fname
    if fpath.exists():
        if validator_fn:
            result = validator_fn(fpath)
            if isinstance(result, tuple):
                file_issues, extra = result
                if repo_name_holder is not None and extra:
                    repo_name_holder[0] = extra
            else:
                file_issues = result
            _record_file_result(fname, file_issues, all_issues, file_statuses)
        else:
            file_statuses[fname] = ValidationStatus.PASS.value
    elif required_for_native:
        all_issues.append(ValidationIssue(
            file=fname, reason="missing_required_file",
            repair=[
                f"'{fname}' is required for a native governed repo.",
                "Run: keyhole init vertical — to scaffold the governance files.",
            ],
        ))
        file_statuses[fname] = ValidationStatus.REJECT.value


def _run_keyhole_yaml(path: Path):
    """Wrapper to unify return type for _validate_present_or_required."""
    issues, repo_name = validate_keyhole_yaml(path)
    return issues, repo_name


def _run_governance_contract(path: Path):
    return validate_governance_contract(path), None


def _record_file_result(
    fname: str,
    issues: List[ValidationIssue],
    all_issues: List[ValidationIssue],
    file_statuses: Dict[str, str],
) -> None:
    """Update file_statuses and all_issues from a list of issues for one file."""
    all_issues.extend(issues)
    if not issues:
        file_statuses[fname] = ValidationStatus.PASS.value
        return
    has_reject = any(not _issue_is_warn_only(i.reason) for i in issues)
    has_warn = any(_issue_is_warn_only(i.reason) for i in issues)
    if has_reject:
        file_statuses[fname] = ValidationStatus.REJECT.value
    elif has_warn:
        file_statuses[fname] = ValidationStatus.WARN.value
    else:
        file_statuses[fname] = ValidationStatus.PASS.value


# Reason codes that produce WARN rather than REJECT
_WARN_REASONS = frozenset({
    "missing_optional_schema_version",
    "missing_optional_trust_metadata",
})


def _issue_is_warn_only(reason: str) -> bool:
    return reason in _WARN_REASONS


def _validate_capability_name_field(
    file_label: str,
    field_path: str,
    cap: str,
) -> List[ValidationIssue]:
    """§8.5, §9 — Validate a capability identifier using SDK-CLIENT-03 rules."""
    from keyhole_sdk.capability.namespace import validate_capability_name
    result = validate_capability_name(cap)
    if result.valid:
        return []
    repair = [
        f"'{cap}' is not a valid capability namespace.",
        "Expected: <domain>.<category>.<capability>.v<major>",
        "Example:  payment.stripe.integration.v1",
    ]
    if result.suggestion:
        repair.append(f"Did you mean: {result.suggestion}?")
    return [ValidationIssue(
        file=file_label,
        field=field_path,
        reason="invalid_capability_namespace",
        repair=repair,
    )]
