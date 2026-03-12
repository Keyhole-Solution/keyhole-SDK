"""Identity surface — whoami and identity inspection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from keyhole_sdk.exceptions import SchemaError
from keyhole_sdk.models import RuntimeIdentity

if TYPE_CHECKING:
    from keyhole_sdk.transport.http import HttpTransport


class IdentitySurface:
    """Identity operations: whoami, identity inspection."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def whoami(self) -> RuntimeIdentity:
        """Return typed runtime identity (GET /identity)."""
        data = self._transport.request("GET", "/identity")
        try:
            return RuntimeIdentity.model_validate(data)
        except ValidationError as exc:
            raise SchemaError(
                f"Identity response does not match RuntimeIdentity model: {exc}",
                raw_data=data,
            ) from exc
