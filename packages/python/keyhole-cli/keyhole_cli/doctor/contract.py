"""`keyhole doctor` — CE-V5-S41-08 contract types.

Canonical schemas, reason codes, invariant names, and data shapes for
the environment doctor surface.  All contracts are deterministic,
hashable, and replay-stable.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOCTOR_SCHEMA_VERSION = "environment-doctor/v1.0"
DOCTOR_CONTRACT_VERSION = "v1.0"

SUPPORTED_PLATFORMS = frozenset({"linux", "darwin", "win32"})
MIN_PYTHON_VERSION = (3, 9)
MAX_PYTHON_VERSION = (3, 13)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DoctorVerdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class OperatingMode(str, Enum):
    AUTO = "auto"
    LOCAL_ONLY = "local_only"
    GOVERNED = "governed"
    HOST_INVENTORY = "host_inventory"
    LIVE_RECONCILIATION = "live_reconciliation"


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class CheckCategory(str, Enum):
    PLATFORM = "platform"
    PYTHON = "python"
    CLI = "cli"
    DOCKER = "docker"
    RUNTIME = "runtime"
    MCP_CONFIG = "mcp_config"
    SDK = "sdk"


class RepairStepKind(str, Enum):
    COMMAND = "command"
    CONFIG_EDIT = "config_edit"
    INSTALL = "install"
    ENV_VAR = "env_var"
    FILE_CREATE = "file_create"
    DOC_LINK = "doc_link"


class RepairAuthority(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ReasonCode(str, Enum):
    DOCTOR_UNSUPPORTED_ENVIRONMENT = "DOCTOR_UNSUPPORTED_ENVIRONMENT"
    DOCTOR_PYTHON_MISSING = "DOCTOR_PYTHON_MISSING"
    DOCTOR_PYTHON_VERSION_UNSUPPORTED = "DOCTOR_PYTHON_VERSION_UNSUPPORTED"
    DOCTOR_CLI_NOT_INSTALLED = "DOCTOR_CLI_NOT_INSTALLED"
    DOCTOR_DOCKER_UNAVAILABLE = "DOCTOR_DOCKER_UNAVAILABLE"
    DOCTOR_COMPOSE_UNAVAILABLE = "DOCTOR_COMPOSE_UNAVAILABLE"
    DOCTOR_RUNTIME_NOT_RUNNING = "DOCTOR_RUNTIME_NOT_RUNNING"
    DOCTOR_RUNTIME_UNREACHABLE = "DOCTOR_RUNTIME_UNREACHABLE"
    DOCTOR_MCP_CONFIG_MISSING = "DOCTOR_MCP_CONFIG_MISSING"
    DOCTOR_GOVERNED_MODE_INCOMPLETE = "DOCTOR_GOVERNED_MODE_INCOMPLETE"
    DOCTOR_LOCAL_MODE_READY = "DOCTOR_LOCAL_MODE_READY"
    DOCTOR_GOVERNED_MODE_READY = "DOCTOR_GOVERNED_MODE_READY"
    DOCTOR_SDK_RUNTIME_VERSION_MISMATCH = "DOCTOR_SDK_RUNTIME_VERSION_MISMATCH"
    DOCTOR_ROOT_FAILURE_IDENTIFIED = "DOCTOR_ROOT_FAILURE_IDENTIFIED"
    DOCTOR_ROOT_FAILURE_UNRESOLVED = "DOCTOR_ROOT_FAILURE_UNRESOLVED"
    REPAIR_PLAN_REQUIRED = "REPAIR_PLAN_REQUIRED"
    REPAIR_STEP_REQUIRES_USER_ACTION = "REPAIR_STEP_REQUIRES_USER_ACTION"
    REPAIR_STEP_REQUIRES_ADMIN_AUTHORITY = "REPAIR_STEP_REQUIRES_ADMIN_AUTHORITY"
    REPAIR_VERIFICATION_FAILED = "REPAIR_VERIFICATION_FAILED"
    REPAIR_VERIFICATION_PASSED = "REPAIR_VERIFICATION_PASSED"
    NO_HIDDEN_MUTATION_ENFORCED = "NO_HIDDEN_MUTATION_ENFORCED"
    DOCTOR_TRUTH_ACCEPTED = "DOCTOR_TRUTH_ACCEPTED"
    DOCTOR_TRUTH_REJECTED = "DOCTOR_TRUTH_REJECTED"
    DOCTOR_PIPX_UNAVAILABLE = "DOCTOR_PIPX_UNAVAILABLE"
    DOCTOR_MCP_BOUNDARY_REACHABLE = "DOCTOR_MCP_BOUNDARY_REACHABLE"
    DOCTOR_MCP_BOUNDARY_UNREACHABLE = "DOCTOR_MCP_BOUNDARY_UNREACHABLE"
    DOCTOR_AUTO_PROMOTED_TO_GOVERNED = "DOCTOR_AUTO_PROMOTED_TO_GOVERNED"
    DOCTOR_PROVISIONING_AVAILABLE = "DOCTOR_PROVISIONING_AVAILABLE"


# ---------------------------------------------------------------------------
# Invariant names sealed by S41-08
# ---------------------------------------------------------------------------

DOCTOR_INVARIANTS = frozenset({
    "INV-DOCTOR-DIAGNOSIS-STRUCTURED",
    "INV-MINIMAL-REPAIR-COMPUTED",
    "INV-REPAIR-JSON-MACHINE-READABLE",
    "INV-NO-HIDDEN-MUTATION",
    "INV-VERIFICATION-AFTER-REPAIR",
    "INV-ROOT-FAILURE-ATTRIBUTABLE",
    "INV-ROLE-SAFE-REPAIR-GUIDANCE",
    "INV-DOCTOR-MODE-AWARE",
})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentFacts:
    """Observable environment facts collected by the doctor."""
    platform: str = ""
    python_available: bool = False
    python_version: str = ""
    python_version_tuple: tuple = ()
    docker_available: bool = False
    docker_version: str = ""
    compose_available: bool = False
    compose_version: str = ""
    cli_installed: bool = False
    cli_version: str = ""
    sdk_installed: bool = False
    sdk_version: str = ""
    runtime_running: bool = False
    runtime_reachable: bool = False
    runtime_url: str = ""
    runtime_version: str = ""
    mcp_config_present: bool = False
    mcp_config_path: str = ""
    mcp_boundary_reachable: bool = False
    mcp_boundary_url: str = ""
    mcp_contract_version: str = ""
    mcp_operations: list = field(default_factory=list)
    pipx_available: bool = False
    is_wsl: bool = False
    os_family: str = ""
    shell: str = ""
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["python_version_tuple"] = list(self.python_version_tuple)
        return d


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    check_name: str
    category: str
    status: str  # CheckStatus value
    reason_code: str = ""
    message: str = ""
    is_root: bool = False
    downstream_of: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RootFailureGroup:
    """A root failure with its downstream symptoms."""
    root_check: str
    root_reason_code: str
    root_message: str
    downstream_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairStep:
    """A single step in the minimal repair plan."""
    step_id: str
    order: int
    kind: str  # RepairStepKind value
    description: str
    command: str = ""
    authority: str = "user"  # RepairAuthority value
    required: bool = True
    addresses_check: str = ""
    addresses_reason_code: str = ""
    verification_hint: str = ""
    doc_link: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairPlan:
    """Minimal repair plan — RestorationSet-style artifact."""
    plan_id: str = field(
        default_factory=lambda: f"repair-{uuid.uuid4().hex[:12]}"
    )
    requested_goal: str = ""
    requested_mode: str = ""
    root_failures_addressed: List[str] = field(default_factory=list)
    steps: List[RepairStep] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class DiagnosticResult:
    """Complete diagnostic result."""
    diagnostic_run_id: str = field(
        default_factory=lambda: f"diag-{uuid.uuid4().hex[:12]}"
    )
    environment_summary: Dict[str, Any] = field(default_factory=dict)
    check_results: List[CheckResult] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    root_failure_groups: List[RootFailureGroup] = field(default_factory=list)
    requested_mode: str = ""
    final_posture: str = ""  # DoctorVerdict value
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnostic_run_id": self.diagnostic_run_id,
            "schema_version": DOCTOR_SCHEMA_VERSION,
            "environment_summary": self.environment_summary,
            "check_results": [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in self.check_results
            ],
            "reason_codes": self.reason_codes,
            "root_failure_groups": [
                g.to_dict() if hasattr(g, "to_dict") else g
                for g in self.root_failure_groups
            ],
            "requested_mode": self.requested_mode,
            "final_posture": self.final_posture,
            "emitted_at": self.emitted_at,
        }


@dataclass
class VerificationResult:
    """Result of verification-after-repair."""
    verification_id: str = field(
        default_factory=lambda: f"verify-{uuid.uuid4().hex[:12]}"
    )
    previous_diagnostic_ref: str = ""
    repair_plan_ref: str = ""
    checks_passed: int = 0
    checks_failed: int = 0
    checks_total: int = 0
    remaining_failures: List[str] = field(default_factory=list)
    verified: bool = False
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairJson:
    """Machine-readable repair JSON artifact per §10.4."""
    doctor_version: str = DOCTOR_SCHEMA_VERSION
    diagnostic_result_ref: str = ""
    repair_plan_ref: str = ""
    environment_facts_summary: Dict[str, Any] = field(default_factory=dict)
    root_failures: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    mode: str = ""
    authority_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DoctorAttestation:
    """Doctor truth & repair attestation per §15.5."""
    attestation_id: str = field(
        default_factory=lambda: f"doc-att-{uuid.uuid4().hex[:12]}"
    )
    diagnostic_result_ref: str = ""
    repair_plan_ref: str = ""
    verification_result_ref: str = ""
    final_outcome: str = ""  # DoctorVerdict value
    reason_codes: List[str] = field(default_factory=list)
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic hashing helpers
# ---------------------------------------------------------------------------


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _deterministic_digest(data: Any) -> str:
    if hasattr(data, "to_dict"):
        raw = _canonical_json(data.to_dict())
    elif isinstance(data, dict):
        raw = _canonical_json(data)
    else:
        raw = _canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
