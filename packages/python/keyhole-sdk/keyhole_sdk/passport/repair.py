"""Passport repair guidance — SDK-CLIENT-05 §17.

Every generation failure must map to at least one actionable next step.
"""

from __future__ import annotations

from typing import Dict, List

_REPAIR_MAP: Dict[str, List[str]] = {
    # ── Path / posture errors ──────────────────────────────────────────────
    "InvalidRepoPath": [
        "Ensure the path exists and is a directory.",
        "Run: keyhole passport generate <path-to-repo>",
    ],
    "ForeignRepoNotReady": [
        "This repo has no Keyhole governance files and is not passport-ready.",
        "Run: keyhole ingest . — to begin the alignment process.",
        "Then run alignment until declared capabilities are established.",
        "See: keyhole align --help",
    ],
    "PartiallyAlignedNotReady": [
        "This repo has partial Keyhole governance files but lacks declared capabilities.",
        "Add a 'produces' list to governance_contract.yaml.",
        "Run: keyhole validate — to confirm declared truth before generating a passport.",
    ],
    # ── Missing source files ───────────────────────────────────────────────
    "MissingKeyholeYaml": [
        "keyhole.yaml is required for authoritative passport generation.",
        "Run: keyhole init vertical — to scaffold the governance files.",
    ],
    "MissingGovernanceContract": [
        "governance_contract.yaml is required for authoritative passport generation.",
        "Run: keyhole init vertical — to scaffold the governance files.",
    ],
    # ── Capability errors ──────────────────────────────────────────────────
    "NoDeclaredCapabilities": [
        "No declared capabilities were found in governance_contract.yaml.",
        "Add at least one entry to the 'produces' list.",
        "Example:  produces:\n    - payment.stripe.integration.v1",
    ],
    "InvalidCapabilityName": [
        "Every declared capability must follow: <domain>.<category>.<capability>.v<major>",
        "Example: payment.stripe.integration.v1",
        "Run: keyhole capability validate <name> — for per-name diagnostics.",
        "Run: keyhole validate — to review all validation issues before generating a passport.",
    ],
    "DuplicateCapabilityDeclaration": [
        "Remove the duplicate capability from governance_contract.yaml.",
        "Each capability may appear at most once in the 'produces' list.",
    ],
    # ── Repo identity errors ───────────────────────────────────────────────
    "MissingRepoIdentity": [
        "The 'repo' field in keyhole.yaml must be a non-empty string.",
        "Example:  repo: my-service-name",
    ],
    # ── Transport safety ───────────────────────────────────────────────────
    "UnsafeRepoName": [
        "The repo name contains characters that are not safe for transport.",
        "Use only alphanumeric characters, hyphens, and underscores in the 'repo' field.",
    ],
    # ── Validation failures ────────────────────────────────────────────────
    "ValidationRejected": [
        "Run: keyhole validate — to review all validation issues before generating a passport.",
        "Fix the flagged issues and try again.",
    ],
    # ── Generic fallback ───────────────────────────────────────────────────
    "_default": [
        "Run: keyhole validate — for structured diagnostics.",
        "Review the generation output and fix the indicated issues.",
    ],
}


def map_passport_repair(error_class: str) -> List[str]:
    """Return actionable repair steps for a passport generation error class.

    §17: Never returns empty list — falls back to generic steps.
    """
    return list(_REPAIR_MAP.get(error_class, _REPAIR_MAP["_default"]))
