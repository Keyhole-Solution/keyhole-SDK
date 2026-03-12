"""Test configuration for S41-01 Public Developer Surface Contract tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
assert (REPO_ROOT / "README.md").exists(), f"Bad repo root: {REPO_ROOT}"

# Ensure services/shared is importable
shared_path = str(REPO_ROOT / "services" / "shared")
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root path."""
    return REPO_ROOT
