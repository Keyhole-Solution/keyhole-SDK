"""Declarations surface — submit governed declarations."""

from __future__ import annotations

from typing import Any, Mapping, Optional, TYPE_CHECKING

from pydantic import ValidationError

from keyhole_sdk.exceptions import SchemaError
from keyhole_sdk.models import RealizationReceipt, RealizationRequest

if TYPE_CHECKING:
    from keyhole_sdk.transport.http import HttpTransport


class DeclarationsSurface:
    """Declaration operations: submit, inspect."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def submit(
        self,
        candidate_digest: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> RealizationReceipt:
        """Submit a bounded declaration request and return a typed receipt."""
        req = RealizationRequest(
            candidate_digest=candidate_digest,
            payload=dict(payload or {}),
        )
        data = self._transport.request("POST", "/realize", json=req.model_dump())
        try:
            return RealizationReceipt.model_validate(data)
        except ValidationError as exc:
            raise SchemaError(
                f"Realize response does not match RealizationReceipt model: {exc}",
                raw_data=data,
            ) from exc
