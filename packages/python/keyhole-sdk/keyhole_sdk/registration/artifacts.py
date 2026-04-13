"""Local artifact loading and snapshotting — SDK-CLIENT-07 §6, §16.

Loads native Keyhole declaration artifacts from a repo directory
and loads ingestion references from local proof state.

Never invents missing governance state. Reports what exists and
what does not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.registration.models import (
    IngestionReference,
    NativeArtifacts,
)

# Supported artifact filenames
_NATIVE_ARTIFACT_FILES = {
    "keyhole": "keyhole.yaml",
    "governance_contract": "governance_contract.yaml",
    "capability_passport": "capability_passport.yaml",
    "dependencies": "dependencies.yaml",
}


def _load_yaml_safe(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file, returning None if missing or malformed."""
    if not path.is_file():
        return None
    try:
        import yaml  # type: ignore[import-untyped]
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        # Fallback: try JSON-style YAML (simple key: value)
        try:
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                return {}
            # Simple fallback for basic YAML without the yaml library
            result: Dict[str, Any] = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, _, val = line.partition(":")
                    result[key.strip()] = val.strip()
            return result if result else {"_raw": text}
        except Exception:
            return None
    except Exception:
        return None


def load_native_artifacts(repo_path: Path) -> NativeArtifacts:
    """Load native Keyhole declaration artifacts from a repo (§6.1).

    Loads each recognized artifact file if present. Returns NativeArtifacts
    with None for any files not found. Never invents missing state.
    """
    artifacts: Dict[str, Any] = {}
    for key, filename in _NATIVE_ARTIFACT_FILES.items():
        artifacts[key] = _load_yaml_safe(repo_path / filename)
    return NativeArtifacts(**artifacts)


def load_ingestion_reference(
    *,
    state_dir: Path,
    ingest_id: str,
) -> Optional[IngestionReference]:
    """Load an ingestion reference from local proof state (§6.2).

    Looks for proof artifacts from a prior ``keyhole ingest`` run.
    Returns None if the reference cannot be found or loaded.
    """
    if not ingest_id:
        return None

    # Look in the ingestion proof directory
    safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in ingest_id)
    proof_dir = state_dir / "ingest" / safe_id

    if not proof_dir.is_dir():
        return None

    # Try to load the response.json for outcome data
    response_path = proof_dir / "response.json"
    request_path = proof_dir / "request.json"

    response_data: Dict[str, Any] = {}
    request_data: Dict[str, Any] = {}

    if response_path.is_file():
        try:
            response_data = json.loads(response_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if request_path.is_file():
        try:
            request_data = json.loads(request_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Extract relevant fields
    pkg_summary = request_data.get("package_summary", request_data)
    repo_identity = pkg_summary.get("repo_identity", "")
    languages = pkg_summary.get("languages", [])
    frameworks = pkg_summary.get("frameworks", [])
    shadow = pkg_summary.get("shadow", False)

    posture = response_data.get("compatibility", "foreign")
    ingestion_id = response_data.get("ingestion_id", ingest_id)
    timestamp = response_data.get("timestamp", request_data.get("timestamp", ""))

    return IngestionReference(
        ingest_id=ingestion_id or ingest_id,
        compatibility_posture=posture,
        repo_identity=repo_identity,
        languages=languages,
        frameworks=frameworks,
        has_keyhole_scaffold=pkg_summary.get("has_keyhole_scaffold", False),
        ingestion_timestamp=timestamp,
    )


def build_artifacts_snapshot(
    *,
    native_artifacts: Optional[NativeArtifacts] = None,
    ingestion_ref: Optional[IngestionReference] = None,
) -> Dict[str, Any]:
    """Build a deterministic snapshot of all registration inputs (§16).

    Captures exactly what was presented to MCP for proof reproducibility.
    """
    snapshot: Dict[str, Any] = {
        "snapshot_type": "registration_inputs",
    }

    if native_artifacts:
        snapshot["native_artifacts"] = native_artifacts.to_snapshot()
    else:
        snapshot["native_artifacts"] = None

    if ingestion_ref:
        snapshot["ingestion_reference"] = ingestion_ref.to_snapshot()
    else:
        snapshot["ingestion_reference"] = None

    return snapshot
