"""Auth attempt registry, sign-out manager, and re-auth hygiene.

SDK-CLIENT-25 §7.4 (auth attempt supersession) and §8 (logout / re-auth).

The :class:`AuthAttemptRegistry` tracks pending device-flow login
attempts so that only the most recent attempt may store credentials.
Late successes from older attempts are dropped — preventing a stale
"approved but unused" device flow from poisoning the local credential
store.

The :class:`SignOutManager` implements the canonical logout sequence:

  1. revoke refresh token at the boundary (best-effort);
  2. delete every local auth artifact (access token, refresh token,
     pending device-flow state, PKCE state, cached metadata);
  3. emit a redacted diagnostic event;
  4. return a typed :class:`LogoutResult`.

After sign-out, the next ``keyhole login`` must behave like first run —
no stale ``initialize`` hang, no skipped login, no resurrected token.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore


# ── Auth attempt registry ──────────────────────────────────────


@dataclass
class AuthAttempt:
    """A single in-flight login attempt."""

    attempt_id: str
    flow: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    superseded: bool = False
    completed: bool = False

    def safe_summary(self) -> Dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "flow": self.flow,
            "created_at": self.created_at.isoformat(),
            "superseded": self.superseded,
            "completed": self.completed,
        }


class AuthAttemptRegistry:
    """In-memory registry of pending login attempts.

    Thread-safe.  When a new attempt starts, every prior pending attempt
    is marked ``superseded=True``.  Pollers that observe their own
    attempt as superseded must abort and never persist credentials.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts: Dict[str, AuthAttempt] = {}
        self._active: Optional[str] = None

    def start(self, flow: str) -> AuthAttempt:
        """Begin a new attempt; supersedes any prior pending attempts."""
        with self._lock:
            for attempt in self._attempts.values():
                if not attempt.completed:
                    attempt.superseded = True
            attempt = AuthAttempt(attempt_id=str(uuid.uuid4()), flow=flow)
            self._attempts[attempt.attempt_id] = attempt
            self._active = attempt.attempt_id
            return attempt

    def is_superseded(self, attempt_id: str) -> bool:
        """Return True iff this attempt has been superseded or unknown."""
        with self._lock:
            attempt = self._attempts.get(attempt_id)
            if attempt is None:
                return True
            return attempt.superseded

    def is_active(self, attempt_id: str) -> bool:
        """Return True iff this attempt is still the active attempt."""
        with self._lock:
            return self._active == attempt_id and not self._attempts[
                attempt_id
            ].superseded

    def complete(self, attempt_id: str) -> None:
        """Mark an attempt as completed (success or terminal failure)."""
        with self._lock:
            attempt = self._attempts.get(attempt_id)
            if attempt is not None:
                attempt.completed = True

    def cancel(self, attempt_id: str) -> None:
        """Mark an attempt as superseded (user cancellation)."""
        with self._lock:
            attempt = self._attempts.get(attempt_id)
            if attempt is not None:
                attempt.superseded = True
                attempt.completed = True

    def cancel_all(self) -> List[str]:
        """Cancel every pending attempt (used on sign-out).

        Returns the list of attempt IDs that were superseded.
        """
        cancelled: List[str] = []
        with self._lock:
            for attempt in self._attempts.values():
                if not attempt.completed:
                    attempt.superseded = True
                    attempt.completed = True
                    cancelled.append(attempt.attempt_id)
            self._active = None
        return cancelled

    def snapshot(self) -> List[AuthAttempt]:
        """Return a snapshot list of all known attempts (for diagnostics)."""
        with self._lock:
            return list(self._attempts.values())


# Module-level default registry — shared across the in-process client.
_default_registry = AuthAttemptRegistry()


def default_registry() -> AuthAttemptRegistry:
    """Return the process-wide default :class:`AuthAttemptRegistry`."""
    return _default_registry


# ── Logout / re-auth hygiene ───────────────────────────────────


@dataclass
class LogoutResult:
    """Outcome of a sign-out invocation."""

    success: bool
    revoked_refresh_token: bool
    revoked_access_token: bool
    cleared_credential_store: bool
    cleared_pending_attempts: List[str]
    cleared_extra_paths: List[str]
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "success": self.success,
            "revoked_refresh_token": self.revoked_refresh_token,
            "revoked_access_token": self.revoked_access_token,
            "cleared_credential_store": self.cleared_credential_store,
            "cleared_pending_attempts": list(self.cleared_pending_attempts),
            "cleared_extra_paths": list(self.cleared_extra_paths),
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
        }


class SignOutManager:
    """Coordinates logout and prevents stale auth state from blocking re-auth.

    Responsibilities (SDK-CLIENT-25 §8.1):

      - revoke refresh / access tokens at the boundary (best-effort);
      - delete every local auth artifact;
      - cancel pending device-flow attempts;
      - emit redacted diagnostic events;
      - never raise a non-recoverable exception — sign-out must always
        leave the local state clean.

    Re-auth (§8.2) is the natural consequence: with no stored credential,
    ``CredentialStore.is_authenticated()`` returns False and the next
    ``login`` invocation begins a fresh transaction.
    """

    def __init__(
        self,
        *,
        credential_store: Optional[CredentialStore] = None,
        registry: Optional[AuthAttemptRegistry] = None,
        revocation_endpoint: Optional[str] = None,
        client_id: Optional[str] = None,
        extra_paths: Optional[List[Path]] = None,
        session: Optional[requests.Session] = None,
        on_event: Optional[Callable[[str, Dict[str, object]], None]] = None,
    ) -> None:
        self._credential_store = credential_store or CredentialStore()
        self._registry = registry or default_registry()
        self._revocation_endpoint = revocation_endpoint
        self._client_id = client_id
        self._extra_paths = list(extra_paths or [])
        self._session = session or requests.Session()
        self._on_event = on_event

    def sign_out(self, *, correlation_id: Optional[str] = None) -> LogoutResult:
        """Execute the full sign-out sequence.

        Always clears local state, even if revocation fails.
        """
        cid = correlation_id or str(uuid.uuid4())
        revoked_access = False
        revoked_refresh = False
        revoke_error: Optional[str] = None

        # 1) Best-effort revocation at the boundary.
        try:
            session = self._credential_store.load()
        except Exception:  # noqa: BLE001 — corrupted store still gets cleared
            session = None

        if session is not None and self._revocation_endpoint and self._client_id:
            if session.refresh_token:
                ok, err = self._revoke(
                    token=session.refresh_token,
                    token_type_hint="refresh_token",
                )
                revoked_refresh = ok
                if not ok and err:
                    revoke_error = err
            if session.access_token:
                ok, err = self._revoke(
                    token=session.access_token,
                    token_type_hint="access_token",
                )
                revoked_access = ok
                if not ok and err and not revoke_error:
                    revoke_error = err

        # 2) Cancel pending attempts so late device-flow approvals are dropped.
        cancelled = self._registry.cancel_all()

        # 3) Clear the credential store unconditionally.
        cleared = True
        try:
            self._credential_store.clear()
        except Exception as exc:  # noqa: BLE001 — surface but never re-raise
            cleared = False
            if not revoke_error:
                revoke_error = f"credential clear failed: {exc}"

        # 4) Best-effort cleanup of any extra session-bound artifacts.
        cleared_extra: List[str] = []
        for path in self._extra_paths:
            try:
                if path.exists():
                    if path.is_dir():
                        _rm_tree(path)
                    else:
                        path.unlink()
                    cleared_extra.append(str(path))
            except Exception:
                # Never let cleanup errors poison the next login.
                continue

        result = LogoutResult(
            success=cleared and revoke_error is None,
            revoked_refresh_token=revoked_refresh,
            revoked_access_token=revoked_access,
            cleared_credential_store=cleared,
            cleared_pending_attempts=cancelled,
            cleared_extra_paths=cleared_extra,
            error_message=revoke_error,
            correlation_id=cid,
        )

        if self._on_event is not None:
            try:
                self._on_event("auth.logout.completed", result.to_safe_dict())
            except Exception:
                pass

        return result

    # ── Internal ──────────────────────────────────────────────

    def _revoke(self, *, token: str, token_type_hint: str) -> tuple[bool, Optional[str]]:
        """Best-effort RFC 7009 token revocation."""
        if not self._revocation_endpoint or not self._client_id:
            return False, None
        try:
            resp = self._session.post(
                self._revocation_endpoint,
                data={
                    "client_id": self._client_id,
                    "token": token,
                    "token_type_hint": token_type_hint,
                },
                timeout=10,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            return False, f"revocation network error: {exc}"
        # RFC 7009: 200 means revoked; many servers also return 204.
        if resp.status_code in (200, 204):
            return True, None
        return False, f"revocation HTTP {resp.status_code}"


def _rm_tree(path: Path) -> None:
    """Recursively delete a directory tree without raising on individual files."""
    for child in path.iterdir():
        try:
            if child.is_dir():
                _rm_tree(child)
            else:
                child.unlink()
        except Exception:
            continue
    try:
        path.rmdir()
    except Exception:
        pass
