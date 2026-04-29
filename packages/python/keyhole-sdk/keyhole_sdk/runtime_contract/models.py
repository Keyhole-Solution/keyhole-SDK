"""Runtime contract models — SDK-CLIENT-24.

Typed representations of the SDK-SERVER-24 runtime contract as returned by:
  - ``GET /mcp/v1/capabilities`` — ``runtime_profiles`` block
  - ``sdk.runtime.surface.get.v1`` run type
  - ``sdk.runtime.compatibility.check.v1`` run type

The client never decides runtime trust. Only the MCP boundary classifies a
runtime as ``canonical_container``, ``external_attested``,
``external_unverified``, or ``unsupported``. These models simply preserve
the server's classification and supporting evidence.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CONTRACT_VERSION = "sdk-runtime-contract.v1"


class RuntimeMode(str, enum.Enum):
    """Runtime mode advertised by the client when checking compatibility."""

    CONTAINER = "container"
    EXTERNAL = "external"
    SHADOW = "shadow"


class RuntimeTrustLevel(str, enum.Enum):
    """Server-classified runtime trust levels (§5)."""

    CANONICAL_CONTAINER = "canonical_container"
    EXTERNAL_ATTESTED = "external_attested"
    EXTERNAL_UNVERIFIED = "external_unverified"
    UNSUPPORTED = "unsupported"


class RuntimeProfileKind(str, enum.Enum):
    """Profile kinds disclosed by the server."""

    CONTAINER = "container"
    EXTERNAL = "external"


class RuntimeCompatibilityStatus(str, enum.Enum):
    """Outcome class of a compatibility check (§9.3-§9.7)."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER = "DEFER"


# ──────────────────────────────────────────────────────────────
# Profile / surface payloads
# ──────────────────────────────────────────────────────────────


@dataclass
class RuntimeProfile:
    """A single runtime profile disclosed by the server (§9.1)."""

    profile_id: str
    kind: RuntimeProfileKind
    canonical: bool = False
    requires_container_runtime: bool = False
    requires_local_venv: bool = False
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "kind": self.kind.value,
            "canonical": self.canonical,
            "requires_container_runtime": self.requires_container_runtime,
            "requires_local_venv": self.requires_local_venv,
            "description": self.description,
        }

    @classmethod
    def from_raw(cls, payload: Dict[str, Any]) -> "RuntimeProfile":
        kind_raw = str(payload.get("kind", "external")).lower()
        try:
            kind = RuntimeProfileKind(kind_raw)
        except ValueError:
            kind = RuntimeProfileKind.EXTERNAL
        return cls(
            profile_id=str(payload.get("profile_id") or payload.get("id") or ""),
            kind=kind,
            canonical=bool(payload.get("canonical", False)),
            requires_container_runtime=bool(
                payload.get("requires_container_runtime", False)
            ),
            requires_local_venv=bool(payload.get("requires_local_venv", False)),
            description=str(payload.get("description", "")),
            raw=dict(payload),
        )


@dataclass
class RuntimeSurfaceResult:
    """Result of ``sdk.runtime.surface.get.v1`` — §9.2."""

    status: str
    contract_version: str
    canonical_profile_id: str = ""
    external_profile_id: str = ""
    profiles: List[RuntimeProfile] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "contract_version": self.contract_version,
            "canonical_profile_id": self.canonical_profile_id,
            "external_profile_id": self.external_profile_id,
            "profiles": [p.to_dict() for p in self.profiles],
        }


# ──────────────────────────────────────────────────────────────
# Compatibility request / context shapes
# ──────────────────────────────────────────────────────────────


@dataclass
class RuntimeContext:
    """Client-built runtime context for compatibility check (§11).

    The client may stamp local runtime claims here; the server alone decides
    the resulting trust level. Never set ``runtime_trust_level`` from the
    client side.
    """

    contract_version: str
    profile_id: str
    runtime_mode: RuntimeMode
    sdk_version: str = ""
    cli_version: str = ""
    runtime_kind: str = ""
    container_image_digest: Optional[str] = None
    runtime_profile_digest: Optional[str] = None
    runtime_claims_digest: Optional[str] = None
    repo_digest: Optional[str] = None
    ctxpack_digest: Optional[str] = None
    execution_adapter: Optional[str] = None
    nonportable_paths: List[str] = field(default_factory=list)
    extra_claims: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Render the runtime context payload for the server."""
        payload: Dict[str, Any] = {
            "contract_version": self.contract_version,
            "profile_id": self.profile_id,
            "runtime_mode": self.runtime_mode.value,
            "sdk_version": self.sdk_version,
            "cli_version": self.cli_version,
        }
        if self.runtime_kind:
            payload["runtime_kind"] = self.runtime_kind
        if self.container_image_digest:
            payload["container_image_digest"] = self.container_image_digest
        if self.runtime_profile_digest:
            payload["runtime_profile_digest"] = self.runtime_profile_digest
        if self.runtime_claims_digest:
            payload["runtime_claims_digest"] = self.runtime_claims_digest
        if self.repo_digest:
            payload["repo_digest"] = self.repo_digest
        if self.ctxpack_digest:
            payload["ctxpack_digest"] = self.ctxpack_digest
        if self.execution_adapter:
            payload["execution_adapter"] = self.execution_adapter
        if self.nonportable_paths:
            payload["nonportable_paths"] = list(self.nonportable_paths)
        if self.extra_claims:
            payload.update(self.extra_claims)
        return payload


@dataclass
class RuntimeRepairGuidance:
    """Server-provided repair guidance (§12.5)."""

    reason: str = ""
    message: str = ""
    affected_field: str = ""
    repair: List[str] = field(default_factory=list)
    next_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason,
            "message": self.message,
            "affected_field": self.affected_field,
            "repair": list(self.repair),
            "next_command": self.next_command,
        }

    @classmethod
    def from_raw(cls, data: Dict[str, Any]) -> "RuntimeRepairGuidance":
        repair_raw = data.get("repair") or data.get("repair_suggestions") or []
        if isinstance(repair_raw, str):
            repair_list = [repair_raw]
        elif isinstance(repair_raw, list):
            repair_list = [str(item) for item in repair_raw if item]
        else:
            repair_list = []
        return cls(
            reason=str(data.get("reason", "")),
            message=str(data.get("message", "")),
            affected_field=str(data.get("affected_field", "")),
            repair=repair_list,
            next_command=str(data.get("next_command", "")),
        )


@dataclass
class RuntimeCompatibilityResult:
    """Result of ``sdk.runtime.compatibility.check.v1`` — §9.3-§9.7."""

    status: RuntimeCompatibilityStatus
    selected_profile: str = ""
    runtime_trust_level: Optional[RuntimeTrustLevel] = None
    contract_version: str = CONTRACT_VERSION
    reason: str = ""
    message: str = ""
    repair: RuntimeRepairGuidance = field(default_factory=RuntimeRepairGuidance)
    run_id: str = ""
    correlation_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status == RuntimeCompatibilityStatus.ACCEPT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "selected_profile": self.selected_profile,
            "runtime_trust_level": (
                self.runtime_trust_level.value if self.runtime_trust_level else None
            ),
            "contract_version": self.contract_version,
            "reason": self.reason,
            "message": self.message,
            "repair": self.repair.to_dict(),
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_raw(
        cls,
        data: Dict[str, Any],
        *,
        correlation_id: str = "",
    ) -> "RuntimeCompatibilityResult":
        status_raw = str(data.get("status", "")).upper()
        # Normalize accepted/rejected/deferred wording
        if status_raw in ("ACCEPTED", "ACCEPT", "OK"):
            status = RuntimeCompatibilityStatus.ACCEPT
        elif status_raw in ("REJECTED", "REJECT", "FAILED"):
            status = RuntimeCompatibilityStatus.REJECT
        elif status_raw in ("DEFERRED", "DEFER", "PENDING"):
            status = RuntimeCompatibilityStatus.DEFER
        else:
            # Default conservative classification when server is silent
            status = RuntimeCompatibilityStatus.REJECT

        trust_raw = data.get("runtime_trust_level")
        trust: Optional[RuntimeTrustLevel] = None
        if isinstance(trust_raw, str) and trust_raw:
            try:
                trust = RuntimeTrustLevel(trust_raw)
            except ValueError:
                trust = None

        repair = RuntimeRepairGuidance.from_raw(data)
        return cls(
            status=status,
            selected_profile=str(data.get("selected_profile", "")),
            runtime_trust_level=trust,
            contract_version=str(
                data.get("contract_version", CONTRACT_VERSION)
            ),
            reason=str(data.get("reason", "")),
            message=str(data.get("message", "")),
            repair=repair,
            run_id=str(data.get("run_id", "")),
            correlation_id=str(data.get("correlation_id", correlation_id)),
            raw=dict(data),
        )


# ──────────────────────────────────────────────────────────────
# Local diagnostics
# ──────────────────────────────────────────────────────────────


@dataclass
class RuntimeDiagnostics:
    """Local runtime diagnostics — never canonical proof truth (§12.3)."""

    container_runtime_detected: bool = False
    container_runtime_kind: str = ""
    inside_container: bool = False
    local_venv_present: bool = False
    local_venv_path: str = ""
    local_venv_canonical: bool = False  # always False — venv is never canonical
    platform: str = ""
    python_version: str = ""
    sdk_version: str = ""
    cli_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_runtime_detected": self.container_runtime_detected,
            "container_runtime_kind": self.container_runtime_kind,
            "inside_container": self.inside_container,
            "local_venv_present": self.local_venv_present,
            "local_venv_path": self.local_venv_path,
            "local_venv_canonical": self.local_venv_canonical,
            "platform": self.platform,
            "python_version": self.python_version,
            "sdk_version": self.sdk_version,
            "cli_version": self.cli_version,
        }


@dataclass
class RuntimeProofArtifact:
    """Proof artifact bundle reference for a runtime contract operation."""

    correlation_id: str
    bundle_dir: str
    files: List[str] = field(default_factory=list)
