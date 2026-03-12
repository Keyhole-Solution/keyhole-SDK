"""SDK exception hierarchy.

Implements §12.4 of CE-V5-S41-05: Predictable Error Surface.

The public surface must distinguish, at minimum:
  - transport/configuration failure   → TransportError
  - authentication failure            → AuthenticationError
  - server rejection                  → PublicEndpointError
  - contract incompatibility          → ContractIncompatibleError
  - polling/result retrieval failure  → RuntimeUnavailableError
  - validation failure                → ValidationError
  - schema mismatch                   → SchemaError
"""

from __future__ import annotations

from typing import Optional


class KeyholeSDKError(Exception):
    """Base exception for all SDK errors."""


class TransportError(KeyholeSDKError):
    """Network / HTTP transport failure (DNS, timeout, connection refused)."""


class AuthenticationError(KeyholeSDKError):
    """Authentication failed — invalid or missing credentials."""


class RuntimeUnavailableError(KeyholeSDKError):
    """The runtime is reachable at TCP level but returned a non-healthy status."""


class SchemaError(KeyholeSDKError):
    """Response from the runtime could not be parsed into the expected typed model."""

    def __init__(self, message: str, raw_data: Optional[dict] = None) -> None:
        super().__init__(message)
        self.raw_data = raw_data


class CompatibilityError(KeyholeSDKError):
    """SDK / runtime are not compatible at the contract level."""


class ContractIncompatibleError(KeyholeSDKError):
    """Client/server contract version mismatch detected."""


class PublicEndpointError(KeyholeSDKError):
    """The runtime returned a structured public error response."""

    def __init__(self, message: str, status_code: int = 0, detail: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ValidationError(KeyholeSDKError):
    """Request payload failed local validation before submission."""
