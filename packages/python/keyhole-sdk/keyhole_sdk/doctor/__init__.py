"""SDK-CLIENT-01-D — Doctor discovery package for host identity reconciliation.

Provides the SDK layer for MCP host inventory, split identity detection,
connection reconciliation, and proof emission.

Modules:
  - models — DoctorHostRecord, DoctorReport, HostDiagnosis, etc.
  - host_inventory — Pluggable host detection (VS Code, JetBrains, Cloud Code, SDK context)
  - diagnostics — Identity classification and repair guidance
  - reconciliation — Full reconciliation flow orchestrator
  - proof — Doctor proof bundle emission
"""

from keyhole_sdk.doctor.models import (  # noqa: F401
    DoctorHostEntry,
    DoctorHostRecord,
    DoctorReport,
    DoctorSummaryStatus,
    HostDiagnosis,
    HostFamily,
    HostSupportStatus,
    HostType,
    RecommendedAction,
    ReconciliationMode,
    ReconnectRequirement,
    RepairGuidance,
    StalenessState,
)
from keyhole_sdk.doctor.host_inventory import (  # noqa: F401
    CloudCodeHostDetector,
    HostDetector,
    JetBrainsHostDetector,
    SDKCredentialDetector,
    VSCodeHostDetector,
    detect_hosts,
)
from keyhole_sdk.doctor.diagnostics import (  # noqa: F401
    build_doctor_report,
    build_repair_guidance,
    classify_host_diagnosis,
)
from keyhole_sdk.doctor.reconciliation import (  # noqa: F401
    CONNECTION_INSPECT_RUN_TYPE,
    CONNECTION_INVALIDATE_RUN_TYPE,
    CONNECTION_LINEAGE_RUN_TYPE,
    CONNECTION_LIST_RUN_TYPE,
    CONNECTION_REBIND_RUN_TYPE,
    CONNECTION_STATUS_RUN_TYPE,
    CONNECTION_SURFACES,
    CONNECTION_WHOAMI_RUN_TYPE,
    check_connection_surfaces_available,
    reconcile,
)
from keyhole_sdk.doctor.proof import DoctorProofBundle  # noqa: F401

__all__ = [
    # Models
    "DoctorHostEntry",
    "DoctorHostRecord",
    "DoctorReport",
    "DoctorSummaryStatus",
    "HostDiagnosis",
    "HostType",
    "RecommendedAction",
    "RepairGuidance",
    "StalenessState",
    # Host inventory
    "HostDetector",
    "SDKCredentialDetector",
    "VSCodeHostDetector",
    "detect_hosts",
    # Diagnostics
    "build_doctor_report",
    "build_repair_guidance",
    "classify_host_diagnosis",
    # Reconciliation
    "CONNECTION_INVALIDATE_RUN_TYPE",
    "CONNECTION_LIST_RUN_TYPE",
    "CONNECTION_REBIND_RUN_TYPE",
    "CONNECTION_SURFACES",
    "CONNECTION_WHOAMI_RUN_TYPE",
    "check_connection_surfaces_available",
    "reconcile",
    # Proof
    "DoctorProofBundle",
]
