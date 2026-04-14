"""Capability namespace exception — SDK-CLIENT-03."""

from __future__ import annotations

from typing import List

from keyhole_sdk.capability.namespace import NamespaceRejectReason


class CapabilityNameError(ValueError):
    """Raised when a capability name fails namespace validation.

    §8.5: Carries the stable reject_reasons list for deterministic handling.
    """

    def __init__(
        self,
        message: str,
        reject_reasons: List[NamespaceRejectReason] | None = None,
    ) -> None:
        super().__init__(message)
        self.reject_reasons: List[NamespaceRejectReason] = reject_reasons or []
