"""Discovery — capabilities retrieval, normalization, and caching.

CE-V5-S42-03: Capabilities Discovery Client.

This package implements the first executable discovery primitive
for the keyhole-developer-kit external participant.

Public entry points:
  CapabilitiesClient   — fetch + normalize GET /mcp/v1/capabilities
  CapabilitiesResult   — normalized capabilities model
  CapabilitiesCache    — local advisory cache for discovery snapshots
"""

from keyhole_sdk.discovery.models import (
    AuthPosture,
    CapabilitiesResult,
    ClientGuidance,
    CompatibilityPosture,
    ConnectionSurfaceContract,
    ConnectionSurfaceRunType,
    ContextAccessContract,
    ContractIdentity,
    DiscoveryMetadata,
    FeatureFlags,
    TransportPosture,
)
from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.discovery.cache import CapabilitiesCache

__all__ = [
    "AuthPosture",
    "CapabilitiesCache",
    "CapabilitiesClient",
    "CapabilitiesResult",
    "ClientGuidance",
    "CompatibilityPosture",
    "ConnectionSurfaceContract",
    "ConnectionSurfaceRunType",
    "ContextAccessContract",
    "ContractIdentity",
    "DiscoveryMetadata",
    "FeatureFlags",
    "TransportPosture",
]
