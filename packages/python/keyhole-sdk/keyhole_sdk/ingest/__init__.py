"""Repository Ingestion — SDK-CLIENT-10.

Public surface for local repository scanning, deterministic packaging,
ingestion submission, proof emission, and repair guidance.
"""

from keyhole_sdk.ingest.models import (
    CompatibilityPosture,
    ConfidenceLevel,
    FileClassification,
    InferredCapability,
    IngestionOutcome,
    IngestionPackage,
    IngestionRequest,
    GraphSummary,
    RepoScanResult,
    ScanSignal,
)
from keyhole_sdk.ingest.scanner import scan_repo
from keyhole_sdk.ingest.filter import IncludeExcludeFilter, DEFAULT_EXCLUDES, DEFAULT_INCLUDES
from keyhole_sdk.ingest.packager import build_ingestion_package
from keyhole_sdk.ingest.submitter import submit_ingestion
from keyhole_sdk.ingest.proof import emit_ingestion_proof
from keyhole_sdk.ingest.repair import map_ingestion_repair

__all__ = [
    # Models
    "CompatibilityPosture",
    "ConfidenceLevel",
    "FileClassification",
    "InferredCapability",
    "IngestionOutcome",
    "IngestionPackage",
    "IngestionRequest",
    "GraphSummary",
    "RepoScanResult",
    "ScanSignal",
    # Scanner
    "scan_repo",
    # Filter
    "IncludeExcludeFilter",
    "DEFAULT_EXCLUDES",
    "DEFAULT_INCLUDES",
    # Packager
    "build_ingestion_package",
    # Submitter
    "submit_ingestion",
    # Proof
    "emit_ingestion_proof",
    # Repair
    "map_ingestion_repair",
]
