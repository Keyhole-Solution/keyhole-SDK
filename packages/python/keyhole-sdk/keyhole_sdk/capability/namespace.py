"""Capability namespace enforcement — SDK-CLIENT-03.

Defines the canonical capability naming contract and provides
deterministic validation, creation helpers, and safe normalization.

Canonical format:  <domain>.<category>.<capability>.v<major>

Examples:
  payment.stripe.integration.v1
  crm.salesforce.sync.v2
  workorder.assignment.engine.v1

§5: Four dot-separated segments — domain, category, capability, version.
§8: Validation rules — character policy, version suffix, reject reasons.
§8.4: Normalization only where builder intent is obvious (whitespace, case).
§8.5: Deterministic reject reasons — stable error class strings.
§9: Advisory-by-default for foreign repos.
§13: same input → same canonical name, same error → same reason code.
"""

from __future__ import annotations

import enum
import re
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Reject reason codes  §8.5
# ─────────────────────────────────────────────────────────────


class NamespaceRejectReason(str, enum.Enum):
    """Stable, deterministic reject reason codes for capability names.

    §8.5: Every invalid name must produce a stable reject reason.
    §13: same invalid input → same reason code, always.
    """

    INVALID_SEGMENT_COUNT = "invalid_segment_count"
    """Name does not contain exactly four dot-separated segments."""

    INVALID_VERSION_SUFFIX = "invalid_version_suffix"
    """Final segment does not match v<positive-integer>."""

    UPPERCASE_NOT_ALLOWED = "uppercase_not_allowed"
    """One or more segments contain uppercase characters."""

    EMPTY_NAMESPACE_SEGMENT = "empty_namespace_segment"
    """One or more of the first three segments is empty."""

    ILLEGAL_CHARACTER = "illegal_character"
    """A segment contains a character not allowed by the character policy."""

    LEADING_ZERO_VERSION = "leading_zero_version"
    """Version major has a leading zero (e.g. v01)."""

    CONSECUTIVE_DOTS = "consecutive_dots"
    """Name contains consecutive dots (empty segment between dots)."""


# ─────────────────────────────────────────────────────────────
# Validation models  §7.3
# ─────────────────────────────────────────────────────────────


class CapabilityValidationResult(BaseModel):
    """Result of validating a capability name against the namespace contract.

    §7.3: validation result must support CLI messages, test assertions,
    ingestion filtering, alignment guidance, and future LSP integration.

    §12.2: messages must teach — show expected format and an example.
    §12.3: suggest corrected form where safe.
    """

    name: str = Field("", description="The input name that was validated.")
    valid: bool = Field(False, description="True if the name satisfies all rules.")
    reject_reasons: List[NamespaceRejectReason] = Field(
        default_factory=list,
        description="All reject reason codes (may be multiple).",
    )
    message: str = Field("", description="Human-readable validation summary.")
    suggestion: str = Field(
        "",
        description="Suggested corrected form where safe, empty if unclear.",
    )
    normalized: str = Field(
        "",
        description="Safe-normalized form (trimmed + lowercased). Empty if invalid.",
    )

    @property
    def is_valid(self) -> bool:
        return self.valid

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "valid": self.valid,
            "reject_reasons": [r.value for r in self.reject_reasons],
            "message": self.message,
            "suggestion": self.suggestion,
            "normalized": self.normalized,
        }


class CapabilityNameParts(BaseModel):
    """Structured parts of a canonical capability name.

    Used by creation helpers to assemble a validated name from components
    before assembling the final dot-separated string.
    """

    domain: str = Field(..., description="Top-level domain (e.g. 'payment').")
    category: str = Field(..., description="Category within domain (e.g. 'stripe').")
    capability: str = Field(..., description="Capability name (e.g. 'integration').")
    major: int = Field(..., ge=1, description="Major version number (positive integer).")

    @property
    def canonical_name(self) -> str:
        """Assemble canonical name from parts."""
        return f"{self.domain}.{self.category}.{self.capability}.v{self.major}"


# ─────────────────────────────────────────────────────────────
# Internal validation helpers  §8
# ─────────────────────────────────────────────────────────────

# §8.2 — allowed character policy for segment content
_SEGMENT_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$|^[a-z0-9]$")
"""Segments may contain: a-z, 0-9, internal hyphens. Must start/end alnum."""

# §8.3 — version segment must be v<positive-integer>, no leading zeros except v1
_VERSION_RE = re.compile(r"^v(0|[1-9][0-9]*)$")
_VERSION_NO_LEADING_ZERO_RE = re.compile(r"^v0[0-9]+$")


def _has_uppercase(s: str) -> bool:
    return any(c.isupper() for c in s)


def _check_segment(seg: str) -> Optional[NamespaceRejectReason]:
    """Return the first reject reason for a single non-version segment, or None."""
    if not seg:
        return NamespaceRejectReason.EMPTY_NAMESPACE_SEGMENT
    if _has_uppercase(seg):
        return NamespaceRejectReason.UPPERCASE_NOT_ALLOWED
    if not _SEGMENT_RE.match(seg):
        return NamespaceRejectReason.ILLEGAL_CHARACTER
    return None


def _check_version_segment(seg: str) -> Optional[NamespaceRejectReason]:
    """Return the first reject reason for the version segment, or None."""
    if not seg:
        return NamespaceRejectReason.EMPTY_NAMESPACE_SEGMENT
    if _has_uppercase(seg):
        return NamespaceRejectReason.UPPERCASE_NOT_ALLOWED
    if _VERSION_NO_LEADING_ZERO_RE.match(seg):
        return NamespaceRejectReason.LEADING_ZERO_VERSION
    if not _VERSION_RE.match(seg):
        return NamespaceRejectReason.INVALID_VERSION_SUFFIX
    return None


def _build_message(name: str, reasons: List[NamespaceRejectReason]) -> str:
    """§12.2: Validation messages must teach."""
    if not reasons:
        return f"'{name}' is a valid capability namespace."
    lines = [
        f"Invalid capability namespace: '{name}'",
        "Expected: <domain>.<category>.<capability>.v<major>",
        "Example:  payment.stripe.integration.v1",
        "Issues:",
    ]
    for r in reasons:
        lines.append(f"  • {_REASON_DESCRIPTIONS[r]}")
    return "\n".join(lines)


_REASON_DESCRIPTIONS: dict[NamespaceRejectReason, str] = {
    NamespaceRejectReason.INVALID_SEGMENT_COUNT: (
        "Must have exactly 4 dot-separated segments (domain.category.capability.vN)"
    ),
    NamespaceRejectReason.INVALID_VERSION_SUFFIX: (
        "Final segment must be v<N> where N is a positive integer (e.g. v1, v2, v10)"
    ),
    NamespaceRejectReason.UPPERCASE_NOT_ALLOWED: (
        "All segments must be lowercase (use 'stripe' not 'Stripe')"
    ),
    NamespaceRejectReason.EMPTY_NAMESPACE_SEGMENT: (
        "No segment may be empty — check for consecutive dots (e.g. 'payment..v1')"
    ),
    NamespaceRejectReason.ILLEGAL_CHARACTER: (
        "Segments may only contain lowercase letters, digits, and internal hyphens"
    ),
    NamespaceRejectReason.LEADING_ZERO_VERSION: (
        "Version major must not have a leading zero (use v1 not v01)"
    ),
    NamespaceRejectReason.CONSECUTIVE_DOTS: (
        "Name contains empty segment(s) — consecutive dots are not allowed"
    ),
}


def _suggest_correction(name: str, reasons: List[NamespaceRejectReason]) -> str:
    """§12.3: Suggest corrected form where builder intent is obvious.

    Only suggests when the fix is unambiguous (whitespace, case, obvious fixes).
    Returns empty string if the correction would require guessing intent.
    """
    # Apply safe normalization
    normalized = _safe_normalize(name)
    if not normalized:
        return ""
    # Re-validate the normalized form
    result = _validate_raw(normalized)
    if result.valid:
        # If normalized form is valid, suggest it
        if normalized != name:
            return normalized
    # Try to build a suggestion from known patterns
    return ""


# ─────────────────────────────────────────────────────────────
# Safe normalization  §8.4
# ─────────────────────────────────────────────────────────────


def _safe_normalize(name: str) -> str:
    """Apply only obvious safe normalizations.

    §8.4: trim whitespace, lowercase, collapse obvious internal spaces.
    Does NOT silently rewrite malformed repo declarations.
    """
    if not isinstance(name, str):
        return ""
    # Trim outer whitespace
    name = name.strip()
    # Replace spaces around dots or at segment boundaries with nothing
    name = re.sub(r"\s*\.\s*", ".", name)
    # Lowercase the entire string (§8.4 — safe obvious normalization)
    name = name.lower()
    return name


def normalize_capability_parts(
    domain: str,
    category: str,
    capability: str,
    major: int | str,
) -> Tuple[str, str, str, int]:
    """Safely normalize incoming parts from interactive/CLI input.

    §8.4: trim, lowercase, coerce major. Used by creation helper before
    displaying to builder for confirmation.

    Returns (domain, category, capability, major_int).
    Raises ValueError if major cannot be coerced to a positive int.
    """
    domain = domain.strip().lower() if isinstance(domain, str) else ""
    category = category.strip().lower() if isinstance(category, str) else ""
    capability = capability.strip().lower() if isinstance(capability, str) else ""
    if isinstance(major, str):
        major = major.strip()
        try:
            major = int(major)
        except (ValueError, TypeError):
            raise ValueError(f"major must be a positive integer, got: {major!r}")
    if not isinstance(major, int) or major < 1:
        raise ValueError(f"major must be a positive integer >= 1, got: {major!r}")
    return domain, category, capability, major


# ─────────────────────────────────────────────────────────────
# Core validation (internal)
# ─────────────────────────────────────────────────────────────


def _validate_raw(name: str) -> CapabilityValidationResult:
    """Core validation logic against the canonical contract."""
    reasons: List[NamespaceRejectReason] = []

    # Fast-check for consecutive dots (empty segment)
    if ".." in name:
        reasons.append(NamespaceRejectReason.CONSECUTIVE_DOTS)
        return CapabilityValidationResult(
            name=name,
            valid=False,
            reject_reasons=reasons,
            message=_build_message(name, reasons),
        )

    parts = name.split(".")
    if len(parts) != 4:
        reasons.append(NamespaceRejectReason.INVALID_SEGMENT_COUNT)
        return CapabilityValidationResult(
            name=name,
            valid=False,
            reject_reasons=reasons,
            message=_build_message(name, reasons),
        )

    domain_seg, category_seg, cap_seg, version_seg = parts

    # Validate first three segments
    for seg in (domain_seg, category_seg, cap_seg):
        err = _check_segment(seg)
        if err and err not in reasons:
            reasons.append(err)

    # Validate version segment
    ver_err = _check_version_segment(version_seg)
    if ver_err and ver_err not in reasons:
        reasons.append(ver_err)

    valid = not bool(reasons)
    normalized = name if valid else ""
    return CapabilityValidationResult(
        name=name,
        valid=valid,
        reject_reasons=reasons,
        message=_build_message(name, reasons),
        normalized=normalized,
    )


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────


def validate_capability_name(name: str) -> CapabilityValidationResult:
    """Validate a capability name against the canonical namespace contract.

    §8: Enforces segment count, character rules, and version suffix.
    §12.2: Returns human-readable message that teaches the correct format.
    §12.3: Suggests corrected form where builder intent is unambiguous.
    §13: Deterministic — same input → same result, always.

    Usage::

        result = validate_capability_name("payment.stripe.integration.v1")
        if not result.valid:
            print(result.message)
            if result.suggestion:
                print(f"Did you mean: {result.suggestion}?")
    """
    if not isinstance(name, str):
        return CapabilityValidationResult(
            name=str(name),
            valid=False,
            reject_reasons=[NamespaceRejectReason.ILLEGAL_CHARACTER],
            message=_build_message(str(name), [NamespaceRejectReason.ILLEGAL_CHARACTER]),
        )

    result = _validate_raw(name)

    # §12.3 — attempt a useful suggestion
    if not result.valid:
        suggestion = _suggest_correction(name, result.reject_reasons)
        return CapabilityValidationResult(
            name=result.name,
            valid=False,
            reject_reasons=result.reject_reasons,
            message=result.message,
            suggestion=suggestion,
        )

    return result


def create_capability_name(
    domain: str,
    category: str,
    capability: str,
    major: int,
) -> str:
    """Assemble and return a validated canonical capability name.

    §5: Returns ``<domain>.<category>.<capability>.v<major>``.
    §6.1: Creation helper — validates parts and assembles the name.
    §13: Same input → same canonical name, always.

    Raises ``CapabilityNameError`` if the assembled name fails validation.

    Usage::

        name = create_capability_name("payment", "stripe", "integration", 1)
        # → "payment.stripe.integration.v1"
    """
    assembled = f"{domain}.{category}.{capability}.v{major}"
    result = validate_capability_name(assembled)
    if not result.valid:
        from keyhole_sdk.capability.exceptions import CapabilityNameError
        raise CapabilityNameError(
            f"Cannot create capability name from parts: {result.message}",
            reject_reasons=result.reject_reasons,
        )
    return assembled
