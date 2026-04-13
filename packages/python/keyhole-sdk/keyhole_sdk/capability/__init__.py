"""Capability Discovery and Resolution — SDK-CLIENT-08.

Public surface for governed capability search, deterministic
dependency resolution, and safe materialization.  Supports both
Keyhole-native repos and foreign / ingestion-backed repos.
"""

from keyhole_sdk.capability.models import (
    CapabilityCandidate,
    CapabilitySearchRequest,
    CapabilitySearchResult,
    MaterializationMode,
    RepoPosture,
    ResolutionOutcome,
    ResolutionRequest,
    ResolvedDependency,
)
from keyhole_sdk.capability.search import submit_capability_search
from keyhole_sdk.capability.resolver import submit_resolution
from keyhole_sdk.capability.materializer import materialize_resolution
from keyhole_sdk.capability.proof import (
    emit_search_proof,
    emit_resolution_proof,
)
from keyhole_sdk.capability.repair import map_capability_repair

__all__ = [
    # Models
    "CapabilityCandidate",
    "CapabilitySearchRequest",
    "CapabilitySearchResult",
    "MaterializationMode",
    "RepoPosture",
    "ResolutionOutcome",
    "ResolutionRequest",
    "ResolvedDependency",
    # Search
    "submit_capability_search",
    # Resolver
    "submit_resolution",
    # Materializer
    "materialize_resolution",
    # Proof
    "emit_search_proof",
    "emit_resolution_proof",
    # Repair
    "map_capability_repair",
]
