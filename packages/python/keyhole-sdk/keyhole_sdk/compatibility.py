"""SDK / Runtime compatibility validation.

Provides deterministic compatibility assessment between the SDK
and a live Keyhole runtime instance.  Can be invoked standalone
(``python -m keyhole_sdk.compatibility``) or imported.

This module encodes the release compatibility rules from
CE-V5-S41-03 §17.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

from keyhole_sdk.client import KeyholeClient
from keyhole_sdk.models import CompatibilityResult, CompatibilityStatus


# ──────────────────────────────────────────────────────────────
# Release Compatibility Rule Constants
# ──────────────────────────────────────────────────────────────

COMPATIBILITY_RULES = {
    "compatible_changes": [
        "Adding optional public fields",
        "Adding non-breaking public helper behavior",
        "Preserving all required semantics",
    ],
    "conditionally_compatible_changes": [
        "Adding new public capabilities not yet modeled by the SDK",
        "Adding optional surface details the SDK can safely ignore",
    ],
    "incompatible_changes": [
        "Removing required public fields",
        "Renaming required public fields",
        "Changing required field meaning",
        "Changing receipt semantics",
        "Changing environment/mode meaning",
        "Introducing reliance on private/internal fields",
    ],
    "promotion_rule": (
        "Incompatible drift must produce REJECT unless explicitly "
        "coordinated through governed versioning."
    ),
}


def check(
    base_url: str,
    *,
    timeout: float = 10.0,
) -> CompatibilityResult:
    """Run a deterministic compatibility check against a live runtime.

    Returns a :class:`CompatibilityResult` describing the outcome.
    """
    client = KeyholeClient(base_url, timeout=timeout)
    try:
        return client.check_compatibility()
    finally:
        client.close()


def check_and_report(
    base_url: str,
    *,
    timeout: float = 10.0,
    output_file: Optional[str] = None,
) -> CompatibilityResult:
    """Check compatibility and optionally write JSON report to *output_file*."""
    result = check(base_url, timeout=timeout)
    report = result.model_dump()
    report["compatibility_status"] = result.compatibility_status.value
    if output_file:
        with open(output_file, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    return result


# ──────────────────────────────────────────────────────────────
# Standalone entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from keyhole_sdk.config import DEFAULT_BASE_URL
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    res = check(url)
    print(json.dumps(res.model_dump(), indent=2, default=str))
    sys.exit(0 if res.compatibility_status != CompatibilityStatus.INCOMPATIBLE else 1)
