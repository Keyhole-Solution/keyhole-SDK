"""Identity mismatch detection — SDK-CLIENT-25 §9.

The client never *decides* identity — only the MCP boundary's
``whoami`` response is canonical.  But when multiple surfaces (VS Code
extension and CLI, for example) bind to different identities on the
same machine, the client must surface the divergence rather than
silently merging them.

This module compares two server-resolved :class:`WhoamiResponse`
objects (or their dict equivalents) and returns a typed
:class:`IdentityMatchResult`.  No JWT decoding is ever performed — the
match is computed from server-issued user identifiers only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from keyhole_sdk.auth_bootstrap.models import WhoamiResponse


# Fields compared for identity equality.  Tenant/org are included so
# that the same user-id under a different tenancy is still flagged.
_COMPARE_FIELDS = ("user_id", "tenant_id", "org_id")


class IdentityMismatchError(Exception):
    """Raised when the caller asks for a strict identity match and detects
    divergence between two surfaces."""


@dataclass
class IdentityMatchResult:
    """Outcome of an identity comparison."""

    matched: bool
    differing_fields: List[str] = field(default_factory=list)
    a_summary: Dict[str, Any] = field(default_factory=dict)
    b_summary: Dict[str, Any] = field(default_factory=dict)
    a_label: str = "a"
    b_label: str = "b"

    def to_safe_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "differing_fields": list(self.differing_fields),
            "a_label": self.a_label,
            "b_label": self.b_label,
            "a_summary": dict(self.a_summary),
            "b_summary": dict(self.b_summary),
        }

    def warning_text(self) -> str:
        """Render the §9 user-facing mismatch warning."""
        if self.matched:
            return ""
        a = self.a_summary.get("user_id") or "<unknown>"
        b = self.b_summary.get("user_id") or "<unknown>"
        return (
            "Detected Keyhole identity mismatch.\n\n"
            f"{self.a_label} is connected as: {a}\n"
            f"{self.b_label} appears connected as: {b}\n\n"
            "Choose one:\n"
            f"- Use {self.a_label} identity\n"
            f"- Re-authenticate {self.a_label}\n"
            f"- Re-authenticate {self.b_label}\n"
        )


WhoamiLike = Union[WhoamiResponse, Dict[str, Any], None]


def _coerce(whoami: WhoamiLike) -> Dict[str, Any]:
    """Project a whoami-like value into the comparison subset."""
    if whoami is None:
        return {}
    if isinstance(whoami, WhoamiResponse):
        data = whoami.model_dump(mode="json")
    elif isinstance(whoami, dict):
        data = dict(whoami)
    else:
        raise TypeError(
            f"unsupported whoami type for identity comparison: {type(whoami)!r}"
        )
    return {field_name: data.get(field_name) for field_name in _COMPARE_FIELDS}


def detect_identity_mismatch(
    a: WhoamiLike,
    b: WhoamiLike,
    *,
    a_label: str = "VS Code",
    b_label: str = "CLI",
    raise_on_mismatch: bool = False,
) -> IdentityMatchResult:
    """Compare two server-resolved identities.

    Args:
        a: First whoami (e.g. VS Code extension's resolved identity).
        b: Second whoami (e.g. CLI's resolved identity).
        a_label / b_label: Surface labels used in user-facing messages.
        raise_on_mismatch: If True, raise :class:`IdentityMismatchError`
            instead of returning a result with ``matched=False``.

    Returns:
        :class:`IdentityMatchResult` describing the comparison.
    """
    a_summary = _coerce(a)
    b_summary = _coerce(b)

    # If either side is unknown we cannot detect mismatch.  Mark matched
    # so callers don't false-positive on an unauthenticated surface.
    if not a_summary or not b_summary:
        return IdentityMatchResult(
            matched=True,
            a_summary=a_summary,
            b_summary=b_summary,
            a_label=a_label,
            b_label=b_label,
        )

    differing: List[str] = []
    for field_name in _COMPARE_FIELDS:
        av = a_summary.get(field_name)
        bv = b_summary.get(field_name)
        # Treat None / "" as "not asserted" rather than mismatch.
        if not av or not bv:
            continue
        if av != bv:
            differing.append(field_name)

    matched = not differing
    result = IdentityMatchResult(
        matched=matched,
        differing_fields=differing,
        a_summary=a_summary,
        b_summary=b_summary,
        a_label=a_label,
        b_label=b_label,
    )

    if not matched and raise_on_mismatch:
        raise IdentityMismatchError(result.warning_text())
    return result
