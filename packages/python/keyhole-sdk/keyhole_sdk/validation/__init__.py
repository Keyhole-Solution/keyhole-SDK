"""Governance contract and dependency schema validation — SDK-CLIENT-04.

Public surface for the ``keyhole_sdk.validation`` package.

All consumer-facing names and callables are re-exported here.  Internal
sub-modules (detector, parser, validator, repair, proof) must be accessed
through this ``__init__`` — do not import them directly from application code.
"""

from __future__ import annotations

from keyhole_sdk.validation.models import (
    ContractRepoPosture,
    NormalizedDependency,
    NormalizationPreview,
    ReadinessLevel,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from keyhole_sdk.validation.detector import (
    ALL_KEYHOLE_FILES,
    FOREIGN_MANIFESTS,
    NATIVE_SIGNALS,
    PARTIAL_SIGNALS,
    detect_foreign_manifests,
    detect_repo_posture,
)
from keyhole_sdk.validation.validator import (
    run_validation,
    validate_capability_passport,
    validate_dependencies,
    validate_governance_contract,
    validate_keyhole_yaml,
)
from keyhole_sdk.validation.compatibility import validate_compatibility
from keyhole_sdk.validation.repair import map_validation_repair
from keyhole_sdk.validation.proof import emit_validation_proof

__all__ = [
    # models
    "ValidationStatus",
    "ContractRepoPosture",
    "ReadinessLevel",
    "ValidationIssue",
    "NormalizedDependency",
    "NormalizationPreview",
    "ValidationResult",
    # detector
    "NATIVE_SIGNALS",
    "PARTIAL_SIGNALS",
    "ALL_KEYHOLE_FILES",
    "FOREIGN_MANIFESTS",
    "detect_repo_posture",
    "detect_foreign_manifests",
    # validator
    "validate_keyhole_yaml",
    "validate_governance_contract",
    "validate_capability_passport",
    "validate_dependencies",
    "run_validation",
    # compatibility
    "validate_compatibility",
    # repair
    "map_validation_repair",
    # proof
    "emit_validation_proof",
]
