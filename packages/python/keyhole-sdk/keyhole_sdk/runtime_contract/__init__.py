"""SDK-CLIENT-24 — Runtime contract verification.

Public exports for runtime profile discovery, surface negotiation, and
compatibility verification against the SDK-SERVER-24 boundary contract.

The client never decides runtime trust. The MCP boundary is authoritative.
"""

from keyhole_sdk.runtime_contract.builder import RuntimeContextBuilder
from keyhole_sdk.runtime_contract.client import (
    COMPATIBILITY_CHECK_RUN_TYPE,
    RuntimeContractClient,
    SURFACE_GET_RUN_TYPE,
)
from keyhole_sdk.runtime_contract.diagnostics import collect_diagnostics
from keyhole_sdk.runtime_contract.models import (
    CONTRACT_VERSION,
    RuntimeCompatibilityResult,
    RuntimeCompatibilityStatus,
    RuntimeContext,
    RuntimeDiagnostics,
    RuntimeMode,
    RuntimeProfile,
    RuntimeProfileKind,
    RuntimeProofArtifact,
    RuntimeRepairGuidance,
    RuntimeSurfaceResult,
    RuntimeTrustLevel,
)
from keyhole_sdk.runtime_contract.proof import RuntimeContractProofEmitter
from keyhole_sdk.runtime_contract.repair import (
    fill_repair_defaults,
    map_runtime_repair,
)

__all__ = [
    "CONTRACT_VERSION",
    "COMPATIBILITY_CHECK_RUN_TYPE",
    "SURFACE_GET_RUN_TYPE",
    "RuntimeCompatibilityResult",
    "RuntimeCompatibilityStatus",
    "RuntimeContext",
    "RuntimeContextBuilder",
    "RuntimeContractClient",
    "RuntimeContractProofEmitter",
    "RuntimeDiagnostics",
    "RuntimeMode",
    "RuntimeProfile",
    "RuntimeProfileKind",
    "RuntimeProofArtifact",
    "RuntimeRepairGuidance",
    "RuntimeSurfaceResult",
    "RuntimeTrustLevel",
    "collect_diagnostics",
    "fill_repair_defaults",
    "map_runtime_repair",
]
