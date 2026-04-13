"""Digest validation — SDK-CLIENT-16 §6/§10.

Validates ctxpack_digest shape locally before sending to the boundary.
"""

from __future__ import annotations

import re

# Acceptable digest shapes: hex strings (SHA-256/SHA-512) or
# prefixed digests like sha256:<hex>.
_HEX_RE = re.compile(r"^[0-9a-fA-F]{16,128}$")
_PREFIXED_RE = re.compile(r"^[a-z0-9]+:[0-9a-fA-F]{16,128}$")

# Reserved keyword for auto-compile mode
AUTO_KEYWORD = "auto"


def validate_digest(digest: str) -> str | None:
    """Validate a digest string shape.

    Returns None if valid, or an error message if malformed.
    Does not check remote existence — that is the server's authority.
    """
    if not digest:
        return "Digest is empty."
    if digest == AUTO_KEYWORD:
        return None  # 'auto' is a valid keyword, not a literal digest
    if _HEX_RE.match(digest) or _PREFIXED_RE.match(digest):
        return None
    # Allow URL-safe base64-ish strings (some digest formats)
    if re.match(r"^[A-Za-z0-9_\-]{16,128}$", digest):
        return None
    return (
        f"Malformed digest: {digest!r}. "
        "Expected a hex string (32–128 chars) or prefixed format (e.g. sha256:<hex>)."
    )


def is_auto(digest: str) -> bool:
    """Check whether the digest string is the 'auto' keyword."""
    return digest.strip().lower() == AUTO_KEYWORD
