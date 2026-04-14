"""Capability Passport Generation — SDK-CLIENT-05.

Public surface for the ``keyhole_sdk.passport`` package.

All consumer-facing names are re-exported here.
"""

from __future__ import annotations

from keyhole_sdk.passport.models import (
    CapabilityEntry,
    CapabilityPassportArtifact,
    PassportGenerationResult,
    PassportIdentity,
    PassportIssue,
    PassportLineage,
    PassportProof,
    PassportReadiness,
    PassportRepo,
    PassportStatus,
    PassportTransport,
)
from keyhole_sdk.passport.digest import compute_passport_digest, serialize_passport_for_storage
from keyhole_sdk.passport.generator import generate_passport
from keyhole_sdk.passport.repair import map_passport_repair
from keyhole_sdk.passport.proof import emit_passport_proof

__all__ = [
    # models
    "PassportStatus",
    "PassportReadiness",
    "CapabilityEntry",
    "PassportRepo",
    "PassportIdentity",
    "PassportLineage",
    "PassportProof",
    "PassportTransport",
    "CapabilityPassportArtifact",
    "PassportIssue",
    "PassportGenerationResult",
    # digest
    "compute_passport_digest",
    "serialize_passport_for_storage",
    # generator
    "generate_passport",
    # repair
    "map_passport_repair",
    # proof
    "emit_passport_proof",
]
