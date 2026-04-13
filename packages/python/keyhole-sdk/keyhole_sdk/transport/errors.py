"""Transport-layer typed errors for idempotency, retry, and replay.

SDK-CLIENT-15 §17: Error and Outcome Handling.

These errors are typed, deterministic, and carry repair guidance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.exceptions import KeyholeSDKError


class IdempotencyError(KeyholeSDKError):
    """Base class for idempotency-related transport errors."""

    def __init__(
        self,
        message: str,
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        repair_guidance: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.idempotency_key = idempotency_key
        self.repair_guidance = repair_guidance or []


class MissingIdempotencyKeyError(IdempotencyError):
    """A WRITE_IDEMPOTENT_REQUIRED operation was attempted without a key.

    §17.1: This is a client bug or noncompliant code path.
    """

    def __init__(
        self,
        operation: str,
        *,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Operation '{operation}' is classified as WRITE_IDEMPOTENT_REQUIRED "
            f"but no idempotency key was provided. This is a client bug.",
            request_id=request_id,
            repair_guidance=[
                "Ensure the transport client is used for this operation.",
                "Do not bypass the governed transport layer for write-bearing calls.",
            ],
        )
        self.operation = operation


class IdempotencyConflictError(IdempotencyError):
    """The server reported an idempotency key conflict.

    §17.2: Same key reused with materially different semantics.
    """

    def __init__(
        self,
        message: str = "Idempotency key conflict: the server reports this key was "
        "already used with different request semantics.",
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        server_detail: str = "",
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repair_guidance=[
                "Do not retry with the same idempotency key.",
                "Mint a fresh attempt with a new idempotency key if re-submission is intended.",
                "Inspect the original request outcome before retrying.",
            ],
        )
        self.server_detail = server_detail


class RetryExhaustedError(IdempotencyError):
    """All retry attempts have been exhausted.

    §12.4: No unbounded loops.
    """

    def __init__(
        self,
        message: str,
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        attempt_count: int = 0,
        last_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repair_guidance=[
                f"All {attempt_count} retry attempts exhausted.",
                "The same idempotency key is preserved — you may retry manually.",
                "Check network connectivity and server status before retrying.",
            ],
        )
        self.attempt_count = attempt_count
        self.last_error = last_error


class DeferredError(IdempotencyError):
    """The server deferred execution — retry later with the same identity.

    §17.3: Preserve same key, retry later under same attempt identity.
    """

    def __init__(
        self,
        message: str = "Server deferred execution. Retry later with the same identity.",
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repair_guidance=[
                "The server accepted the request but deferred execution.",
                "Retry with the same idempotency key after the indicated delay.",
            ],
        )
        self.retry_after = retry_after


class TransportUnknownError(IdempotencyError):
    """Transport failure after send — execution status is unknown.

    §13 / §17.5: Transport ambiguity is where idempotency matters most.
    """

    def __init__(
        self,
        message: str = "Transport failure after send. Server execution status is unknown.",
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repair_guidance=[
                "The request was sent but no response was received.",
                "This is NOT proof of non-execution — the server may have executed it.",
                "Retry with the SAME idempotency key to safely resolve the ambiguity.",
                "Do NOT mint a new idempotency key for the same logical attempt.",
            ],
        )


class RateLimitedError(IdempotencyError):
    """The server returned a rate-limit response.

    §17.4: Obey backoff and Retry-After, avoid churn storms.
    """

    def __init__(
        self,
        message: str = "Rate limited by server.",
        *,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(
            message,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repair_guidance=[
                "The server is rate-limiting requests.",
                f"Retry after {retry_after}s." if retry_after else "Retry after server-indicated delay.",
                "The same idempotency key is preserved for safe retry.",
            ],
        )
        self.retry_after = retry_after
