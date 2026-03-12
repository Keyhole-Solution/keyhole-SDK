"""Evidence surface — retrieve evidence for returned public refs.

Per §13: evidence retrieval for returned public refs.
Per §23.8: Evidence Retrieval Proof.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from keyhole_sdk.exceptions import PublicEndpointError

if TYPE_CHECKING:
    from keyhole_sdk.transport.http import HttpTransport


class EvidenceSurface:
    """Evidence operations: retrieval by digest reference."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def get_by_digest(self, digest: str) -> dict[str, Any]:
        """Retrieve evidence envelope for a given digest reference.

        Returns the raw evidence envelope dict. Schema may evolve.
        """
        return self._transport.request("GET", f"/evidence/{digest}")

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent evidence entries (where supported).

        Returns a list of evidence envelope dicts.
        Raises PublicEndpointError if the endpoint is not supported.
        """
        data = self._transport.request("GET", f"/evidence?limit={limit}")
        if isinstance(data, list):
            return data
        return data.get("entries", [])
