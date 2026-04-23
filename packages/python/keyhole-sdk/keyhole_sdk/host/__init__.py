"""SDK-CLIENT-01-D / SDK-CLIENT-23 — Host credential installation, reconciliation, and identity attestation.

Provides:
  - installer — Write/update MCP server entries into IDE host configs
  - reconciler — Three-layer identity comparison (CLI ↔ host ↔ server)
  - attestation_store — Local host attestation file I/O (SDK-CLIENT-23)
  - coherence_engine — Identity coherence classification (SDK-CLIENT-23)
"""

from keyhole_sdk.host.installer import (  # noqa: F401
    HostInstallResult,
    install_host_credentials,
)
from keyhole_sdk.host.reconciler import (  # noqa: F401
    ThreeLayerIdentity,
    reconcile_three_layer,
)
from keyhole_sdk.host.attestation_store import (  # noqa: F401
    write_attestation,
    load_attestations,
    load_identity_policy,
    save_identity_policy,
    clear_identity_policy,
    save_principal_hint,
    load_principal_hint,
)
from keyhole_sdk.host.coherence_engine import (  # noqa: F401
    CoherenceResult,
    classify_coherence,
)
