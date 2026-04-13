"""Transport abstractions — stable façade over HTTP internals.

Per §12.1: Internal transport helpers may evolve.
The public façade must remain stable.

SDK-CLIENT-15: Adds governed transport with request identity,
idempotency, retry, and proof metadata.
"""

from keyhole_sdk.transport.http import HttpTransport
from keyhole_sdk.transport.client import GovernedTransport, TransportResult
from keyhole_sdk.transport.idempotency import (
    OperationAttempt,
    generate_idempotency_key,
    generate_request_id,
)
from keyhole_sdk.transport.operation_registry import (
    OperationClass,
    OperationDescriptor,
    RetryPolicy,
    get_all_operations,
    get_operation,
    is_registered,
    register_operation,
    requires_idempotency,
)
from keyhole_sdk.transport.proof_metadata import (
    ClientObservation,
    TransportProofMetadata,
)
from keyhole_sdk.transport.retry import RetryConfig
from keyhole_sdk.transport.errors import (
    DeferredError,
    IdempotencyConflictError,
    IdempotencyError,
    MissingIdempotencyKeyError,
    RateLimitedError,
    RetryExhaustedError,
    TransportUnknownError,
)

__all__ = [
    # Legacy
    "HttpTransport",
    # Governed transport (SDK-CLIENT-15)
    "GovernedTransport",
    "TransportResult",
    # Idempotency
    "OperationAttempt",
    "generate_idempotency_key",
    "generate_request_id",
    # Operation registry
    "OperationClass",
    "OperationDescriptor",
    "RetryPolicy",
    "get_all_operations",
    "get_operation",
    "is_registered",
    "register_operation",
    "requires_idempotency",
    # Proof metadata
    "ClientObservation",
    "TransportProofMetadata",
    # Retry config
    "RetryConfig",
    # Errors
    "DeferredError",
    "IdempotencyConflictError",
    "IdempotencyError",
    "MissingIdempotencyKeyError",
    "RateLimitedError",
    "RetryExhaustedError",
    "TransportUnknownError",
]
