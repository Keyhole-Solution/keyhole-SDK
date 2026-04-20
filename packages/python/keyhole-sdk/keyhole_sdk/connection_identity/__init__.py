"""SDK-CLIENT-01-C — Connection identity package.

Provides the SDK layer for MCP connection identity introspection,
rebinding, and invalidation through the governed run surface.

Modules:
  - models — ConnectionInfo, RebindRequest/Outcome, InvalidateRequest/Outcome
  - client — ConnectionIdentityClient for MCP dispatch
  - errors — Typed errors with repair guidance
  - repair — Concrete repair step builders
  - render — Human-readable and machine-readable rendering helpers
"""

from keyhole_sdk.connection_identity.models import (  # noqa: F401
    ConnectionAuthority,
    ConnectionInfo,
    ConnectionStaleness,
    InvalidateOutcome,
    InvalidateRequest,
    InvalidateStatus,
    RebindOutcome,
    RebindRequest,
    RebindStatus,
)
from keyhole_sdk.connection_identity.client import (  # noqa: F401
    ConnectionIdentityClient,
)
from keyhole_sdk.connection_identity.errors import (  # noqa: F401
    ConnectionIdentityError,
    ConnectionNetworkError,
    ConnectionNotAuthenticatedError,
    ConnectionNotFoundError,
    ConnectionSurfaceUnavailableError,
    RebindRejectedError,
    VerificationFailedError,
)
from keyhole_sdk.connection_identity.repair import (  # noqa: F401
    repair_commands_for_diagnosis,
    repair_steps_for_diagnosis,
)
from keyhole_sdk.connection_identity.render import (  # noqa: F401
    render_connection_info,
    render_connection_list,
    render_invalidate_outcome,
    render_lineage,
    render_rebind_outcome,
)

__all__ = [
    # Models
    "ConnectionAuthority",
    "ConnectionInfo",
    "ConnectionStaleness",
    "InvalidateOutcome",
    "InvalidateRequest",
    "InvalidateStatus",
    "RebindOutcome",
    "RebindRequest",
    "RebindStatus",
    # Client
    "ConnectionIdentityClient",
    # Errors
    "ConnectionIdentityError",
    "ConnectionNetworkError",
    "ConnectionNotAuthenticatedError",
    "ConnectionNotFoundError",
    "ConnectionSurfaceUnavailableError",
    "RebindRejectedError",
    "VerificationFailedError",
    # Repair
    "repair_commands_for_diagnosis",
    "repair_steps_for_diagnosis",
]
