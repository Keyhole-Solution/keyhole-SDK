"""Validation repair guidance — SDK-CLIENT-04 §15.

Maps error classes and reason codes to concrete, actionable repair steps.
Every repair must never be a dead end. §15 repair shape requirement.
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # ── Invalid repo path ──────────────────────────────────────────────────
    "InvalidRepoPath": [
        "Ensure the path exists and is a directory.",
        "Run: keyhole validate <path-to-repo> — with a valid directory path.",
    ],
    # ── Parse errors ───────────────────────────────────────────────────────
    "parse_error": [
        "Fix the YAML syntax in the flagged file.",
        "Validate YAML at https://yaml-online-parser.appspot.com/ or use: python -c 'import yaml; yaml.safe_load(open(\"file.yaml\"))'",
    ],
    # ── Missing files ──────────────────────────────────────────────────────
    "missing_required_file": [
        "Run: keyhole init vertical — to scaffold the governance file structure.",
        "Or create the file manually following the SDK documentation.",
    ],
    # ── keyhole.yaml issues ────────────────────────────────────────────────
    "missing_required_field": [
        "Add the flagged missing field to the governance file.",
        "Consult: keyhole validate --json for exact field paths.",
    ],
    "empty_or_invalid_repo_name": [
        "Set a non-empty string value for the 'repo' field.",
        "Example: repo: my-service-name",
    ],
    "missing_optional_schema_version": [
        "Add 'schema_version: 1' to keyhole.yaml for future compatibility.",
        "This is optional but recommended.",
    ],
    # ── governance_contract.yaml issues ───────────────────────────────────
    "produces_must_be_list": [
        "Ensure 'produces' is a YAML list.",
        "Example:\n  produces:\n    - payment.stripe.integration.v1",
    ],
    "produces_item_must_be_string": [
        "Each item in 'produces' must be a capability name string.",
    ],
    "local_invariants_must_be_list": [
        "Ensure 'local_invariants' is a YAML list of invariant IDs.",
    ],
    "required_tests_must_be_list": [
        "Ensure 'required_tests' is a YAML list of test names or IDs.",
    ],
    # ── capability_passport.yaml issues ───────────────────────────────────
    "capability_must_be_string": [
        "Set 'capability' to a string capability name.",
        "Example: capability: payment.stripe.integration.v1",
    ],
    "delegated_capabilities_must_be_list": [
        "Ensure 'delegated_capabilities' is a YAML list of capability names.",
    ],
    # ── dependencies.yaml issues ───────────────────────────────────────────
    "dependencies_must_be_list": [
        "Ensure 'dependencies' is a YAML list.",
        "Example:\n  dependencies:\n    - capability: crm.salesforce.sync.v1\n      provider: salesforce-adapter",
    ],
    "dependency_must_be_mapping": [
        "Each item in 'dependencies' must be a YAML mapping.",
    ],
    "missing_required_capability": [
        "Add a 'capability' field to the dependency entry.",
        "Example: capability: payment.stripe.integration.v1",
    ],
    "capability_must_be_string": [
        "The 'capability' field must be a string capability name.",
    ],
    "provider_must_be_string": [
        "The 'provider' field must be a string.",
    ],
    "digest_must_be_string": [
        "The 'digest' field must be a string prefixed with sha256:, sha512:, or sha384:.",
    ],
    "unsupported_digest_format": [
        "Recompute or remove the digest.",
        "Supported prefixes: sha256:, sha512:, sha384:.",
    ],
    "duplicate_capability": [
        "Remove the duplicate capability entry from dependencies.yaml.",
        "Each capability should appear at most once in the dependency list.",
    ],
    "invalid_capability_namespace": [
        "Fix the capability name to match: <domain>.<category>.<capability>.v<major>",
        "Example: payment.stripe.integration.v1",
        "Run: keyhole capability validate <name> — for detailed diagnostics.",
    ],
    # ── Foreign repo / advisory ────────────────────────────────────────────
    "native_governance_files_absent": [
        "Run: keyhole ingest . — to begin the alignment process.",
        "Review alignment guidance before native registration.",
    ],
    "foreign_manifests_detected": [
        "Detected dependency manifests can be used during ingestion.",
        "Run: keyhole ingest . — to generate an analysis from these files.",
    ],    # ── SDK-CLIENT-06: Compatibility domain error codes ───────────────────────
    "compatibility_contract_invalid": [
        "Fix the 'compatibility_contracts' field in governance_contract.yaml.",
        "It must be a list of mappings, each with at least a 'capability' key.",
        "Example:\n  compatibility_contracts:\n    - capability: payment.stripe.integration.v1",
    ],
    "self_dependency_detected": [
        "Remove the self-referential entry from dependencies.yaml.",
        "A repo should not list its own produced capabilities as dependencies.",
    ],
    "incompatible_major_version": [
        "Align the major version references across produces and dependencies.",
        "Or add a 'compatibility_contracts' declaration in governance_contract.yaml",
        "to explicitly declare this cross-version relationship.",
    ],
    "dependency_provider_missing": [
        "Add a 'provider' field to the dependency entry in dependencies.yaml.",
        "Example: provider: my-service-adapter",
        "Provider is required in strict mode and strongly recommended in all modes.",
    ],
    "strict_mode_warning_escalated": [
        "This issue was escalated to a failure by --strict mode.",
        "Resolve the underlying issue or run without --strict for advisory output.",
    ],
    "repo_not_native_ready": [
        "The repo is not yet in native governed shape.",
        "Run: keyhole validate --mode native for a full diagnostic.",
        "Run: keyhole init vertical — to scaffold missing governance files.",
    ],    # ── Generic fallback ───────────────────────────────────────────────────
    "unknown": [
        "Run: keyhole validate --json — for structured diagnostics.",
        "Review the validation output for more details.",
    ],
}


def map_validation_repair(error_class: str) -> List[str]:
    """Return actionable repair guidance for a validation error class.

    §15: Every failure must provide next-best repair guidance. Never returns
    an empty list — falls back to generic steps.
    """
    return _REPAIR_MAP.get(error_class) or _REPAIR_MAP["unknown"]
