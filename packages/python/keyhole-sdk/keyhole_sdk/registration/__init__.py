"""Repository Registration — SDK-CLIENT-07.

Public surface for repository registration with the MCP boundary.
Supports both native governed repo registration and ingestion-backed
registration for foreign repos.
"""

from keyhole_sdk.registration.models import (
    IdentityBinding,
    IngestionReference,
    NativeArtifacts,
    RegistrationOutcome,
    RegistrationPayload,
    RegistrationReadiness,
    RegistrationRequest,
    RegistrationSource,
)
from keyhole_sdk.registration.readiness import assess_readiness
from keyhole_sdk.registration.artifacts import (
    load_native_artifacts,
    load_ingestion_reference,
    build_artifacts_snapshot,
)
from keyhole_sdk.registration.payload import build_registration_payload
from keyhole_sdk.registration.submitter import submit_registration
from keyhole_sdk.registration.proof import emit_registration_proof
from keyhole_sdk.registration.repair import map_registration_repair

__all__ = [
    # Models
    "IdentityBinding",
    "IngestionReference",
    "NativeArtifacts",
    "RegistrationOutcome",
    "RegistrationPayload",
    "RegistrationReadiness",
    "RegistrationRequest",
    "RegistrationSource",
    # Readiness
    "assess_readiness",
    # Artifacts
    "load_native_artifacts",
    "load_ingestion_reference",
    "build_artifacts_snapshot",
    # Payload
    "build_registration_payload",
    # Submitter
    "submit_registration",
    # Proof
    "emit_registration_proof",
    # Repair
    "map_registration_repair",
]
