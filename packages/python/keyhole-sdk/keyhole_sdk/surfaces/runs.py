"""Runs surface — retrieve run state and results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from keyhole_sdk.exceptions import SchemaError
from keyhole_sdk.models import RuntimeState

if TYPE_CHECKING:
    from keyhole_sdk.transport.http import HttpTransport


class RunsSurface:
    """Run/result operations: state retrieval, result inspection."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def get_state(self) -> RuntimeState:
        """Return typed runtime state (GET /state)."""
        data = self._transport.request("GET", "/state")
        try:
            return RuntimeState.model_validate(data)
        except ValidationError as exc:
            raise SchemaError(
                f"State response does not match RuntimeState model: {exc}",
                raw_data=data,
            ) from exc
