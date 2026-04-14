"""Governance contract and dependency schema validation models — SDK-CLIENT-04.

§2: Validation must distinguish native governed validation, foreign/advisory
    validation, and readiness assessment.
§13: Structured output shape is stable and deterministic.
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ── Status and posture enums ──────────────────────────────────────────────────


class ValidationStatus(str, enum.Enum):
    """§10.3: Top-level and per-file validation status."""
    PASS = "PASS"
    WARN = "WARN"
    REJECT = "REJECT"


class ContractRepoPosture(str, enum.Enum):
    """§8.1: Repo posture — must be deterministic and visible in output.

    Distinct from capability.models.RepoPosture (which adds INGESTION_BACKED).
    This posture is specific to governance contract validation.
    """
    NATIVE = "native"
    FOREIGN = "foreign"
    PARTIALLY_ALIGNED = "partially_aligned"


class ReadinessLevel(str, enum.Enum):
    """§10.3: Top-level posture/readiness summary."""
    NATIVE_READY = "native_ready"
    PARTIALLY_ALIGNED = "partially_aligned"
    FOREIGN = "foreign"
    NOT_READY = "not_ready"


# ── Issue model ───────────────────────────────────────────────────────────────


class ValidationIssue(BaseModel):
    """§15: Repair-oriented issue with exact file, field, reason, and steps.

    §15: Every validation failure must surface exact file/field path,
    deterministic reason code, and actionable repair guidance.
    """

    file: str = Field("", description="File where the issue was found.")
    field: str = Field("", description="Exact field path within the file (e.g. dependencies[0].provider).")
    reason: str = Field(..., description="Deterministic reason code.")
    repair: List[str] = Field(default_factory=list, description="Actionable repair steps.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "field": self.field,
            "reason": self.reason,
            "repair": self.repair,
        }


# ── Normalization preview ─────────────────────────────────────────────────────


class NormalizedDependency(BaseModel):
    """Preview of how one dependency will normalize at the boundary."""
    capability: str = ""
    provider: str = ""
    digest: str = ""
    normalized_capability: str = ""


class NormalizationPreview(BaseModel):
    """§8.7, §11.5: Preview normalization before boundary submission.

    The client may preview normalization; the server remains the final authority.
    """
    dependencies: List[NormalizedDependency] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependencies": [d.model_dump() for d in self.dependencies],
        }


# ── Result model ──────────────────────────────────────────────────────────────


class ValidationResult(BaseModel):
    """§13: Structured validation result.

    Stable output shape — same repo contents + mode → same result.
    Matches the §13 structured output contract.
    """

    status: ValidationStatus
    repo_posture: ContractRepoPosture
    readiness: ReadinessLevel
    repo: str = Field("", description="Repo name from keyhole.yaml or directory name.")
    files: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-file status values (PASS/WARN/REJECT).",
    )
    issues: List[ValidationIssue] = Field(default_factory=list)
    normalization_preview: NormalizationPreview = Field(default_factory=NormalizationPreview)
    mode: str = Field("auto", description="Validation mode that was applied.")
    repo_path: str = Field("", description="Resolved repo path.")

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS

    @property
    def rejected(self) -> bool:
        return self.status == ValidationStatus.REJECT

    def to_dict(self) -> Dict[str, Any]:
        """§13: Stable serialisation matching the §13 output contract."""
        return {
            "status": self.status.value,
            "repo_posture": self.repo_posture.value,
            "readiness": self.readiness.value,
            "repo": self.repo,
            "files": self.files,
            "issues": [i.to_dict() for i in self.issues],
            "normalization_preview": self.normalization_preview.to_dict(),
            "mode": self.mode,
            "repo_path": self.repo_path,
        }
