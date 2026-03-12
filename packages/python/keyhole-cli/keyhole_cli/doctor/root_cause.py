"""`keyhole doctor` — CE-V5-S41-08 root failure clustering.

Groups diagnostic failures into root causes and downstream symptoms.
A root failure is one not caused by another failure.
"""
from __future__ import annotations

from typing import Dict, List, Set

from .contract import (
    CheckResult,
    CheckStatus,
    DiagnosticResult,
    ReasonCode,
    RootFailureGroup,
)

# check_name → checks it can cause to fail
DEPENDENCY_MAP: Dict[str, List[str]] = {
    "python_available": ["python_version", "cli_installed"],
    "docker_available": ["compose_available", "runtime_running"],
    "runtime_running": ["runtime_reachable"],
}


def compute_root_failures(
    diagnostic: DiagnosticResult,
) -> List[RootFailureGroup]:
    """Identify root failures and group downstream symptoms."""
    failed_checks: Dict[str, CheckResult] = {
        c.check_name: c
        for c in diagnostic.check_results
        if c.status == CheckStatus.FAIL.value
    }
    if not failed_checks:
        return []

    # Build downstream mapping
    downstream_of: Dict[str, str] = {}
    for c in failed_checks.values():
        if c.downstream_of and c.downstream_of in failed_checks:
            downstream_of[c.check_name] = c.downstream_of

    for root_name, dependents in DEPENDENCY_MAP.items():
        if root_name in failed_checks:
            for dep in dependents:
                if dep in failed_checks and dep not in downstream_of:
                    downstream_of[dep] = root_name

    # Root failures = not downstream of anything
    root_names: Set[str] = {
        name for name in failed_checks if name not in downstream_of
    }

    groups: List[RootFailureGroup] = []
    for root_name in sorted(root_names):
        root_check = failed_checks[root_name]
        downstream = _collect_downstream(root_name, downstream_of)
        groups.append(
            RootFailureGroup(
                root_check=root_name,
                root_reason_code=root_check.reason_code,
                root_message=root_check.message,
                downstream_checks=sorted(downstream),
            )
        )
    return groups


def _collect_downstream(
    root: str,
    downstream_of: Dict[str, str],
) -> List[str]:
    """Collect all checks transitively downstream of *root*."""
    result: List[str] = []
    for check_name, parent in downstream_of.items():
        if parent == root and check_name != root:
            result.append(check_name)
            result.extend(_collect_downstream(check_name, downstream_of))
    return result


def annotate_diagnostic_with_roots(
    diagnostic: DiagnosticResult,
) -> DiagnosticResult:
    """Compute root failures and update the diagnostic in-place."""
    groups = compute_root_failures(diagnostic)
    diagnostic.root_failure_groups = groups

    root_names = {g.root_check for g in groups}
    downstream_names: Set[str] = set()
    for g in groups:
        downstream_names.update(g.downstream_checks)

    for c in diagnostic.check_results:
        if c.check_name in root_names:
            c.is_root = True
        if c.check_name in downstream_names:
            c.is_root = False
            for g in groups:
                if c.check_name in g.downstream_checks:
                    c.downstream_of = g.root_check
                    break

    if groups:
        rc = ReasonCode.DOCTOR_ROOT_FAILURE_IDENTIFIED.value
        if rc not in diagnostic.reason_codes:
            diagnostic.reason_codes.append(rc)
            diagnostic.reason_codes = sorted(set(diagnostic.reason_codes))

    return diagnostic
