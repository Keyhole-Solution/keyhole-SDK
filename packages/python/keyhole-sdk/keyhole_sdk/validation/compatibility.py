"""Compatibility validation — SDK-CLIENT-06 §7.4.

Cross-file compatibility checks:
- compatibility_contracts field shape in governance_contract.yaml
- Self-dependency detection (same cap in produces and consumed deps)
- Incompatible major-line references (same base name, different major versions)

All checks are local-only and deterministic.  The server remains the final
authority for governance invariants.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from keyhole_sdk.validation.models import ValidationIssue

# Matches <any.dotted.name>.v<digits>
_NAMESPACE_VER_RE = re.compile(r"^(.+)\.v(\d+)$")


def validate_compatibility(
    produces: List[str],
    consumed: List[str],
    *,
    gc_data: Optional[Dict] = None,
) -> List[ValidationIssue]:
    """§7.4 — Cross-file compatibility validation.

    Checks:
    1. compatibility_contracts field shape (if present in governance_contract.yaml)
    2. Self-dependency detection (cap in both produces and consumed deps)
    3. Incompatible major-line references (same base, different major versions
       in produces vs consumed)

    Args:
        produces:  Capability names from governance_contract.yaml ``produces``.
        consumed:  Capability names from dependencies.yaml ``dependencies``.
        gc_data:   Raw governance_contract.yaml data for field-level checks.

    Returns:
        List of ValidationIssue.  Empty list means no compatibility concerns.
    """
    issues: List[ValidationIssue] = []

    # ── 1. compatibility_contracts field shape ────────────────────────────
    if gc_data and isinstance(gc_data, dict):
        compat_contracts = gc_data.get("compatibility_contracts")
        if compat_contracts is not None:
            if not isinstance(compat_contracts, list):
                issues.append(ValidationIssue(
                    file="governance_contract.yaml",
                    field="compatibility_contracts",
                    reason="compatibility_contract_invalid",
                    repair=[
                        "'compatibility_contracts' must be a YAML list of mappings.",
                        "Example:\n  compatibility_contracts:\n    - capability: payment.stripe.integration.v1\n      min_version: 1",
                    ],
                ))
            else:
                for idx, entry in enumerate(compat_contracts):
                    if not isinstance(entry, dict):
                        issues.append(ValidationIssue(
                            file="governance_contract.yaml",
                            field=f"compatibility_contracts[{idx}]",
                            reason="compatibility_contract_invalid",
                            repair=[
                                f"compatibility_contracts[{idx}] must be a mapping.",
                                "Each entry needs at least a 'capability' key.",
                            ],
                        ))
                    elif "capability" not in entry:
                        issues.append(ValidationIssue(
                            file="governance_contract.yaml",
                            field=f"compatibility_contracts[{idx}].capability",
                            reason="compatibility_contract_invalid",
                            repair=[
                                f"Add a 'capability' field to compatibility_contracts[{idx}].",
                                "Example: capability: payment.stripe.integration.v1",
                            ],
                        ))

    # ── 2. Self-dependency detection ──────────────────────────────────────
    produces_set = {p for p in produces if isinstance(p, str)}
    seen_self_deps: set = set()
    for cap in consumed:
        if isinstance(cap, str) and cap in produces_set and cap not in seen_self_deps:
            seen_self_deps.add(cap)
            issues.append(ValidationIssue(
                file="dependencies.yaml",
                field="",
                reason="self_dependency_detected",
                repair=[
                    f"'{cap}' appears in both 'produces' and dependencies.",
                    "A repo should not declare itself as a dependency.",
                    "Remove this capability from dependencies.yaml.",
                ],
            ))

    # ── 3. Incompatible major-line references ─────────────────────────────
    def _base_ver(name: str):
        m = _NAMESPACE_VER_RE.match(name)
        if m:
            return m.group(1), int(m.group(2))
        return None, None

    # Map base → produced major version
    produces_bases: Dict[str, int] = {}
    for cap in produces:
        if isinstance(cap, str):
            base, ver = _base_ver(cap)
            if base is not None:
                produces_bases[base] = ver

    # Check consumed caps for version conflicts with produced caps
    seen_conflicts: set = set()
    for cap in consumed:
        if not isinstance(cap, str):
            continue
        base, con_ver = _base_ver(cap)
        if base is None or base not in produces_bases:
            continue
        prod_ver = produces_bases[base]
        if prod_ver != con_ver and base not in seen_conflicts:
            seen_conflicts.add(base)
            issues.append(ValidationIssue(
                file="dependencies.yaml",
                field="",
                reason="incompatible_major_version",
                repair=[
                    f"This repo produces '{base}.v{prod_ver}' but consumes '{cap}' (v{con_ver}).",
                    "If this cross-version dependency is intentional, add a "
                    "compatibility_contracts declaration in governance_contract.yaml.",
                    "Otherwise align the version references across files.",
                ],
            ))

    return issues
