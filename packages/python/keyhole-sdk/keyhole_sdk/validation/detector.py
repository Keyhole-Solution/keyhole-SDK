"""Repo posture detection for governance contract validation — SDK-CLIENT-04.

§8.1: The client must determine whether the repo is native, foreign, or
partially_aligned. Posture selection must be deterministic and visible.

§8.2: For native repos, locate canonical governance files.
      For foreign repos, inspect local dependency sources without
      pretending Keyhole files should already exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from keyhole_sdk.validation.models import ContractRepoPosture

# ── Signal file lists ─────────────────────────────────────────────────────────

# Files whose presence indicates a Keyhole-native repo
NATIVE_SIGNALS: List[str] = [
    "keyhole.yaml",
    "governance_contract.yaml",
]

# Files whose presence indicates partial Keyhole alignment but not full native
PARTIAL_SIGNALS: List[str] = [
    "capability_passport.yaml",
    "dependencies.yaml",
]

# All canonical governance files (for discovery / iteration)
ALL_KEYHOLE_FILES: List[str] = NATIVE_SIGNALS + PARTIAL_SIGNALS

# Foreign repo dependency manifests (§9.5) — advisory detection only
FOREIGN_MANIFESTS: List[str] = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "pom.xml",
    "Gemfile",
    "Cargo.toml",
    "build.gradle",
    "composer.json",
]


def detect_repo_posture(repo_path: Path) -> ContractRepoPosture:
    """§8.1 — Deterministically detect repo governance posture.

    Returns:
        NATIVE          — at least one native governance signal file is present.
        PARTIALLY_ALIGNED — partial governance files present but no native signals.
        FOREIGN         — no Keyhole governance files found at all.
    """
    has_native = any((repo_path / f).exists() for f in NATIVE_SIGNALS)
    if has_native:
        return ContractRepoPosture.NATIVE

    has_partial = any((repo_path / f).exists() for f in PARTIAL_SIGNALS)
    if has_partial:
        return ContractRepoPosture.PARTIALLY_ALIGNED

    return ContractRepoPosture.FOREIGN


def detect_foreign_manifests(repo_path: Path) -> List[str]:
    """§8.2, §9.5 — Detect foreign dependency manifests for advisory reporting.

    Returns a stable-ordered list of detected manifest files.
    Only reports files that actually exist in the repo.
    """
    found = []
    for fname in FOREIGN_MANIFESTS:
        if (repo_path / fname).exists():
            found.append(fname)
    return found
