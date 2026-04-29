"""Redaction-first local diagnostics — SDK-CLIENT-25 §11.

The client must produce structured local diagnostics for the auth
lifecycle (capabilities fetched, flow selected, polling pending, etc.)
without leaking any of the following:

  - access_token / refresh_token
  - id_token
  - device_code
  - authorization headers
  - magic-link URLs (verification_uri_complete query)
  - raw email addresses

This module centralizes redaction and provides a small file-backed
recorder so callers do not invent ad-hoc logging formats.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Field names whose values are always replaced with ``"***redacted***"``.
_SECRET_FIELDS = frozenset({
    "access_token",
    "refresh_token",
    "id_token",
    "device_code",
    "authorization",
    "Authorization",
    "client_secret",
    "password",
    "code_verifier",
})

# Field names that contain magic links (user-shareable URLs with a
# ``user_code`` payload).  We replace them with a redacted placeholder
# but preserve the host so operators can still reason about the boundary.
_LINK_FIELDS = frozenset({
    "verification_uri_complete",
    "magic_link",
    "login_url",
})

# Field names containing raw email addresses.
_EMAIL_FIELDS = frozenset({
    "email",
    "user_email",
})

_REDACTED = "***redacted***"

# Match common token-shaped substrings in free text (JWTs and opaque
# bearer tokens of >=20 chars made of url-safe characters).
_TOKEN_LIKE_RE = re.compile(
    r"(?P<scheme>Bearer\s+)(?P<token>[A-Za-z0-9._\-=]{20,})"
)
_JWT_LIKE_RE = re.compile(r"eyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}")
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")


def _redact_email(value: str) -> str:
    """Mask an email address: keep first letter and domain TLD."""
    if not value or "@" not in value:
        return _REDACTED
    local, _, domain = value.partition("@")
    local_mask = (local[:1] + "***") if local else "***"
    return f"{local_mask}@{domain}"


def _redact_link(value: str) -> str:
    """Drop the query/fragment of a magic link URL but keep host."""
    if not value:
        return _REDACTED
    # Cheap parse — avoid pulling urllib for a hot path.
    try:
        scheme_idx = value.index("://")
    except ValueError:
        return _REDACTED
    rest = value[scheme_idx + 3 :]
    host = rest.split("/", 1)[0]
    scheme = value[:scheme_idx]
    return f"{scheme}://{host}/<redacted>"


def _redact_value(field_name: str, value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(field_name, v) for v in value]
    if field_name in _SECRET_FIELDS:
        return _REDACTED
    if field_name in _LINK_FIELDS and isinstance(value, str):
        return _redact_link(value)
    if field_name in _EMAIL_FIELDS and isinstance(value, str):
        return _redact_email(value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    """Apply free-text redaction to a string.

    Scrubs:
      - ``Authorization: Bearer <token>`` headers
      - JWT-shaped substrings
      - email addresses
    """
    if not text:
        return text
    text = _TOKEN_LIKE_RE.sub(lambda m: f"{m.group('scheme')}{_REDACTED}", text)
    text = _JWT_LIKE_RE.sub(_REDACTED, text)
    text = _EMAIL_RE.sub(lambda m: _redact_email(m.group(0)), text)
    return text


# ── Diagnostic events ──────────────────────────────────────────


@dataclass
class DiagnosticEvent:
    """A single redacted diagnostic event."""

    event: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    correlation_id: Optional[str] = None

    def to_safe_dict(self) -> Dict[str, Any]:
        safe_payload = {
            k: _redact_value(k, v) for k, v in self.payload.items()
        }
        return {
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "payload": safe_payload,
        }


class DiagnosticRecorder:
    """Append-only redacted diagnostic recorder.

    Diagnostics are written as JSON-lines to a per-process log file.
    The recorder also keeps an in-memory buffer for tests and for the
    evidence renderer.
    """

    def __init__(
        self,
        *,
        log_path: Optional[Path] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self._log_path = log_path
        self._correlation_id = correlation_id or str(uuid.uuid4())
        self._buffer: List[DiagnosticEvent] = []

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    @property
    def events(self) -> List[DiagnosticEvent]:
        return list(self._buffer)

    def record(self, event: str, payload: Optional[Dict[str, Any]] = None) -> DiagnosticEvent:
        """Record a diagnostic event with redaction applied."""
        ev = DiagnosticEvent(
            event=event,
            payload=dict(payload or {}),
            correlation_id=self._correlation_id,
        )
        self._buffer.append(ev)
        if self._log_path is not None:
            try:
                self._log_path.parent.mkdir(parents=True, exist_ok=True)
                with self._log_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(ev.to_safe_dict()) + "\n")
            except OSError:
                # Diagnostics must never break the auth flow.
                pass
        return ev

    def export_safe(self) -> List[Dict[str, Any]]:
        """Return the full event buffer as redacted dicts."""
        return [e.to_safe_dict() for e in self._buffer]
