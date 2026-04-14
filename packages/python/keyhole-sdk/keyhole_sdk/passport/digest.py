"""Deterministic digest/serialization for capability passport — SDK-CLIENT-05.

§11: The digest must be stable across:
  - reruns on the same repo
  - different machines with the same effective repo state
  - repeated generation with no declared changes

§11: The digest must NOT incorporate:
  - machine-specific absolute paths
  - uncontrolled timestamps
  - host-ephemeral values

The digest basis is the canonical JSON of the passport payload minus the
``transport.generated_at`` and ``transport.digest`` fields themselves
(which are derived metadata, not source truth).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def _stable_json(obj: Any) -> str:
    """Serialise obj to a compact, sorted-key JSON string for digest purposes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_passport_digest(
    repo_name: str,
    capabilities: List[str],
    *,
    owner: str = "",
    repo_id: str = "",
    parent_repo: str = "",
    parent_passport_digest: str = "",
    schema_version: str = "v1",
) -> str:
    """§11 — Compute a deterministic sha256 digest over canonical passport content.

    The digest basis includes:
    - schema_version
    - repo identity (repo_name, repo_id, owner)
    - sorted capability names
    - lineage hints (parent_repo, parent_passport_digest)

    Explicitly excluded from digest basis:
    - generated_at timestamp
    - the digest field itself (obviously)
    - absolute filesystem paths
    - any machine-local ephemeral values

    Returns "sha256:<hex>" string.
    """
    basis: Dict[str, Any] = {
        "schema_version": schema_version,
        "repo": {
            "owner": owner,
            "repo_id": repo_id,
            "repo_name": repo_name,
        },
        "capabilities": sorted(capabilities),
        "lineage": {
            "parent_passport_digest": parent_passport_digest,
            "parent_repo": parent_repo,
        },
    }
    raw = _stable_json(basis).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def serialize_passport_for_storage(payload: Dict[str, Any]) -> str:
    """§11: Deterministic, human-readable YAML serialization of a passport payload.

    Uses ordered fields matching §10 canonical shape. Falls back to JSON if
    pyyaml is not installed so the artifact is always producible.
    """
    try:
        import yaml  # soft dependency

        # Reconstruct the payload in §10 canonical order before dumping.
        ordered = _canonical_ordered(payload)
        return yaml.dump(
            ordered,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    except ImportError:
        return json.dumps(payload, indent=2, sort_keys=False)


def _canonical_ordered(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict following §10 canonical section order.

    Field order in output YAML:
      schema_version → artifact_kind → repo → identity → capabilities
      → lineage → proof → transport
    """
    ordered: Dict[str, Any] = {}
    for key in (
        "schema_version",
        "artifact_kind",
        "repo",
        "identity",
        "capabilities",
        "lineage",
        "proof",
        "transport",
    ):
        if key in payload:
            ordered[key] = payload[key]
    # Include any unexpected extra keys at the end (forward-compat)
    for key, val in payload.items():
        if key not in ordered:
            ordered[key] = val
    return ordered
