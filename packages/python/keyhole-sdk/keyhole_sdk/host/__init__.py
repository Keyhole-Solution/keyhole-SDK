"""SDK-CLIENT-01-D — Host credential installation and reconciliation.

Provides:
  - installer — Write/update MCP server entries into IDE host configs
  - reconciler — Three-layer identity comparison (CLI ↔ host ↔ server)
"""

from keyhole_sdk.host.installer import (  # noqa: F401
    HostInstallResult,
    install_host_credentials,
)
from keyhole_sdk.host.reconciler import (  # noqa: F401
    ThreeLayerIdentity,
    reconcile_three_layer,
)
