"""SDK-CLIENT-01-C — Connection identity client (§9).

Dispatches connection identity operations through the governed
MCP boundary via POST /mcp/v1/runs/start.

INV-SDK-CLIENT-01-C-006: Rebind/invalidate are idempotent.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import requests

from keyhole_sdk.connection_identity.errors import (
    ConnectionNetworkError,
    ConnectionNotFoundError,
    ConnectionSurfaceUnavailableError,
    RebindRejectedError,
)
from keyhole_sdk.connection_identity.models import (
    ConnectionInfo,
    InvalidateOutcome,
    InvalidateRequest,
    InvalidateStatus,
    RebindOutcome,
    RebindRequest,
    RebindStatus,
)
from keyhole_sdk.config import DEFAULT_BASE_URL as _DEFAULT_MCP_URL
from keyhole_sdk.envelope import unwrap_mcp_envelope
_RUNS_START_PATH = "/mcp/v1/runs/start"


class ConnectionIdentityClient:
    """Client for connection identity operations (§9).

    Dispatches connection.list.inspect, connection.identity.inspect,
    connection.lineage.inspect, connection.rebind, and
    connection.invalidate through the governed run surface.

    INV-SDK-CLIENT-01-C-008: Surface remains governed.
    """

    def __init__(
        self,
        *,
        mcp_base_url: str = _DEFAULT_MCP_URL,
        timeout: int = 30,
    ) -> None:
        self._mcp_base_url = mcp_base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self, access_token: str, idempotency_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Idempotency-Key": idempotency_key,
            "X-Request-Id": idempotency_key,
        }

    def _post(
        self,
        payload: Dict[str, Any],
        access_token: str,
        idempotency_key: str,
    ) -> requests.Response:
        try:
            return requests.post(
                f"{self._mcp_base_url}{_RUNS_START_PATH}",
                json=payload,
                headers=self._headers(access_token, idempotency_key),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ConnectionNetworkError(str(exc)) from exc

    # ── connection.list.inspect (§9.2) ───────────────────────

    def list_connections(
        self,
        *,
        access_token: str,
        correlation_id: Optional[str] = None,
    ) -> List[ConnectionInfo]:
        """List visible MCP connections from the server."""
        cid = correlation_id or str(uuid.uuid4())
        idem = str(uuid.uuid4())

        payload = {
            "run_type": "connection.list.inspect",
            "parameters": {},
            "correlation_id": cid,
        }

        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        if resp.status_code == 404:
            return []

        data = unwrap_mcp_envelope(raw)
        connections = data.get("connections", [])
        if isinstance(connections, list):
            return [self._parse_connection(c) for c in connections]

        return []

    # ── connection.identity.inspect (§9.3) ────────────────

    def connection_inspect(
        self,
        *,
        access_token: str,
        host_id: str = "",
        connection_id: str = "",
        correlation_id: Optional[str] = None,
    ) -> ConnectionInfo:
        """Inspect active identity for a specific connection or host."""
        cid = correlation_id or str(uuid.uuid4())
        idem = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "run_type": "connection.identity.inspect",
            "parameters": {},
            "correlation_id": cid,
        }
        if host_id:
            payload["parameters"]["host_id"] = host_id
        if connection_id:
            payload["parameters"]["connection_id"] = connection_id

        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        if resp.status_code == 404 or raw.get("ok") is False:
            raise ConnectionNotFoundError(
                host_id=host_id, connection_id=connection_id
            )

        return self._parse_connection(unwrap_mcp_envelope(raw))

    # Back-compat alias
    connection_whoami = connection_inspect

    # ── connection.status.inspect (§9.3 optional) ─────────

    def connection_status(
        self,
        *,
        access_token: str,
        host_id: str = "",
        connection_id: str = "",
        correlation_id: Optional[str] = None,
    ) -> ConnectionInfo:
        """Inspect status for a specific connection or host."""
        cid = correlation_id or str(uuid.uuid4())
        idem = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "run_type": "connection.status.inspect",
            "parameters": {},
            "correlation_id": cid,
        }
        if host_id:
            payload["parameters"]["host_id"] = host_id
        if connection_id:
            payload["parameters"]["connection_id"] = connection_id

        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        if resp.status_code == 404 or raw.get("ok") is False:
            raise ConnectionNotFoundError(
                host_id=host_id, connection_id=connection_id
            )

        return self._parse_connection(unwrap_mcp_envelope(raw))

    # ── connection.lineage.inspect (§9.4) ─────────────

    def connection_lineage(
        self,
        *,
        access_token: str,
        host_id: str = "",
        connection_id: str = "",
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspect connection identity lineage (§9.4)."""
        cid = correlation_id or str(uuid.uuid4())
        idem = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "run_type": "connection.lineage.inspect",
            "parameters": {},
            "correlation_id": cid,
        }
        if host_id:
            payload["parameters"]["host_id"] = host_id
        if connection_id:
            payload["parameters"]["connection_id"] = connection_id

        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        if resp.status_code == 404 or raw.get("ok") is False:
            raise ConnectionNotFoundError(
                host_id=host_id, connection_id=connection_id
            )

        return unwrap_mcp_envelope(raw)

    # ── connection.rebind (§9.5) ──────────────────────────

    def rebind(
        self,
        request: RebindRequest,
        *,
        access_token: str,
    ) -> RebindOutcome:
        """Request rebinding of a connection to a different principal.

        INV-SDK-CLIENT-01-C-006: Uses idempotency headers.
        """
        idem = str(uuid.uuid4())

        payload = request.to_run_payload()
        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        return self._classify_rebind_outcome(
            status_code=resp.status_code,
            raw=raw,
            request=request,
        )

    # ── connection.invalidate (§9.6) ──────────────────────

    def invalidate(
        self,
        request: InvalidateRequest,
        *,
        access_token: str,
    ) -> InvalidateOutcome:
        """Invalidate a stale or wrong-principal connection.

        INV-SDK-CLIENT-01-C-006: Uses idempotency headers.
        """
        idem = str(uuid.uuid4())

        payload = request.to_run_payload()
        resp = self._post(payload, access_token, idem)
        raw = resp.json()
        self._check_envelope_error(raw)

        return self._classify_invalidate_outcome(
            status_code=resp.status_code,
            raw=raw,
            request=request,
        )

    # ── Internal helpers ──────────────────────────────────

    @staticmethod
    def _check_envelope_error(raw: Dict[str, Any]) -> None:
        """Raise immediately for SCOPE_DENIED — applies to all operations.

        Other ok:false error codes are handled by the individual callers or
        classifiers so they can map to the correct typed outcome.

        INV-SDK-CLIENT-01-C-008: Surface remains governed.
        """
        if raw.get("ok") is False:
            code = raw.get("error", {}).get("code", "UNKNOWN")
            if code == "SCOPE_DENIED":
                msg = raw.get("error", {}).get("message", "Scope not available.")
                raise ConnectionSurfaceUnavailableError(msg, surface="connection")

    @staticmethod
    def _parse_connection(data: Dict[str, Any]) -> ConnectionInfo:
        from keyhole_sdk.connection_identity.models import (
            ConnectionAuthority,
            ConnectionStaleness,
        )

        authority_raw = str(data.get("authority", "unknown")).lower()
        try:
            authority = ConnectionAuthority(authority_raw)
        except ValueError:
            authority = ConnectionAuthority.UNKNOWN

        staleness_raw = str(data.get("staleness_state", "unknown")).lower()
        try:
            staleness = ConnectionStaleness(staleness_raw)
        except ValueError:
            staleness = ConnectionStaleness.UNKNOWN

        return ConnectionInfo(
            connection_id=data.get("connection_id", ""),
            host_hint=data.get("host_hint", data.get("host_id", "")),
            principal=data.get("principal", data.get("principal_label", "")),
            user_id=data.get("user_id", data.get("principal_user_id", "")),
            authority=authority,
            purpose=data.get("purpose", ""),
            origin=data.get("origin", ""),
            bound_at=data.get("bound_at", ""),
            staleness_state=staleness,
            session_lineage_id=data.get("session_lineage_id", ""),
            supports_rebind=bool(data.get("supports_rebind", False)),
            supports_invalidate=bool(data.get("supports_invalidate", False)),
        )

    @staticmethod
    def _classify_rebind_outcome(
        *,
        status_code: int,
        raw: Dict[str, Any],
        request: RebindRequest,
    ) -> RebindOutcome:
        """Classify server rebind response into typed outcome (§13.5).

        SCOPE_DENIED is already raised upstream by _check_envelope_error.
        """
        if raw.get("ok") is False:
            code = raw.get("error", {}).get("code", "UNKNOWN")
            message = raw.get("error", {}).get("message", "Rebind blocked.")
            inner = raw.get("data") or {}
            run_id = inner.get("run_id", "") if isinstance(inner, dict) else ""
            repair: List[str]
            if code == "REBIND_FORBIDDEN":
                repair = [
                    "This connection does not support rebind.",
                    "Check the connection definition.",
                ]
            elif code == "TARGET_PRINCIPAL_INVALID":
                repair = [
                    "Verify the target profile and user ID.",
                    "Retry with a valid identity.",
                ]
            else:
                repair = [
                    "Inspect the server's rejection reason.",
                    "Verify the target profile and session.",
                    "Retry with a valid identity.",
                ]
            return RebindOutcome(
                status=RebindStatus.REJECTED,
                connection_id=request.connection_id,
                run_id=run_id,
                server_message=message,
                repair_guidance=repair,
            )

        data = unwrap_mcp_envelope(raw)
        run_id = data.get("run_id", "")
        message = data.get("message", data.get("error", ""))
        old_principal = data.get("old_principal", "")
        new_principal = data.get("new_principal", request.target_profile)

        if status_code in (200, 201, 202):
            status_raw = str(data.get("status", "accepted")).lower()
            try:
                status = RebindStatus(status_raw)
            except ValueError:
                status = RebindStatus.ACCEPTED
            return RebindOutcome(
                status=status,
                connection_id=data.get("connection_id", request.connection_id),
                old_principal=old_principal,
                new_principal=new_principal,
                run_id=run_id,
                server_message=str(message),
            )

        if 400 <= status_code < 500:
            return RebindOutcome(
                status=RebindStatus.REJECTED,
                connection_id=request.connection_id,
                old_principal=old_principal,
                run_id=run_id,
                server_message=str(message),
                repair_guidance=[
                    "Inspect the server's rejection reason.",
                    "Verify the target profile and session.",
                    "Retry with a valid identity.",
                ],
            )

        return RebindOutcome(
            status=RebindStatus.REJECTED,
            connection_id=request.connection_id,
            run_id=run_id,
            server_message=f"Server error ({status_code}): {message}",
            repair_guidance=["Retry later or contact support."],
        )

    @staticmethod
    def _classify_invalidate_outcome(
        *,
        status_code: int,
        raw: Dict[str, Any],
        request: InvalidateRequest,
    ) -> InvalidateOutcome:
        """Classify server invalidate response into typed outcome (§13.6).

        SCOPE_DENIED is already raised upstream by _check_envelope_error.
        """
        if raw.get("ok") is False:
            code = raw.get("error", {}).get("code", "UNKNOWN")
            message = raw.get("error", {}).get("message", "Invalidate blocked.")
            inner = raw.get("data") or {}
            run_id = inner.get("run_id", "") if isinstance(inner, dict) else ""
            repair: List[str]
            if code == "INVALIDATE_FORBIDDEN":
                repair = [
                    "This connection does not support invalidation.",
                    "Check the connection definition.",
                ]
            elif code == "CONNECTION_NOT_FOUND":
                repair = [
                    "The specified connection was not found.",
                    "Run 'keyhole connections list' to see visible connections.",
                ]
            else:
                repair = [
                    "Inspect the server's rejection reason.",
                    "Verify the connection exists.",
                ]
            return InvalidateOutcome(
                status=InvalidateStatus.REJECTED,
                connection_id=request.connection_id,
                run_id=run_id,
                server_message=message,
                repair_guidance=repair,
            )

        data = unwrap_mcp_envelope(raw)
        run_id = data.get("run_id", "")
        message = data.get("message", data.get("error", ""))

        if status_code in (200, 201, 202):
            status_raw = str(data.get("status", "accepted")).lower()
            if status_raw == "already_invalidated":
                status = InvalidateStatus.ALREADY_INVALIDATED
            else:
                try:
                    status = InvalidateStatus(status_raw)
                except ValueError:
                    status = InvalidateStatus.ACCEPTED
            return InvalidateOutcome(
                status=status,
                connection_id=data.get("connection_id", request.connection_id),
                reconnect_required=bool(data.get("reconnect_required", True)),
                run_id=run_id,
                server_message=str(message),
            )

        if 400 <= status_code < 500:
            return InvalidateOutcome(
                status=InvalidateStatus.REJECTED,
                connection_id=request.connection_id,
                run_id=run_id,
                server_message=str(message),
                repair_guidance=[
                    "Inspect the server's rejection reason.",
                    "Verify the connection exists.",
                ],
            )

        return InvalidateOutcome(
            status=InvalidateStatus.REJECTED,
            connection_id=request.connection_id,
            run_id=run_id,
            server_message=f"Server error ({status_code}): {message}",
            repair_guidance=["Retry later or contact support."],
        )
