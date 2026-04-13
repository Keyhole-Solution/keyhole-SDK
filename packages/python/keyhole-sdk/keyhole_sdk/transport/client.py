"""Governed transport client — idempotent, retry-safe, proof-aware.

SDK-CLIENT-15 §15.1: The base transport layer must own request-id
injection, idempotency-key injection, retry logic, backoff handling,
Retry-After handling, replay/defer/conflict normalization, and
support metadata capture.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from keyhole_sdk.auth import AuthProvider
from keyhole_sdk.exceptions import (
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.transport.errors import (
    DeferredError,
    IdempotencyConflictError,
    MissingIdempotencyKeyError,
    RateLimitedError,
    RetryExhaustedError,
    TransportUnknownError,
)
from keyhole_sdk.transport.idempotency import (
    OperationAttempt,
    generate_idempotency_key,
    generate_request_id,
)
from keyhole_sdk.transport.operation_registry import (
    OperationClass,
    OperationDescriptor,
    RetryPolicy,
    get_operation,
    requires_idempotency,
)
from keyhole_sdk.transport.proof_metadata import (
    ClientObservation,
    TransportProofMetadata,
)
from keyhole_sdk.transport.retry import (
    RetryConfig,
    compute_backoff_delay,
    is_conflict_status,
    is_rate_limited,
    is_retryable_status,
    parse_retry_after,
    sleep_for_backoff,
)


class TransportResult:
    """Result of a governed transport call with proof metadata."""

    def __init__(
        self,
        data: Dict[str, Any],
        status_code: int,
        proof: TransportProofMetadata,
        response_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.data = data
        self.status_code = status_code
        self.proof = proof
        self.response_headers = response_headers or {}


class GovernedTransport:
    """Transport client with request identity, idempotency, retry, and proof.

    This wraps the low-level HTTP transport and adds:
    - X-Request-Id on every request (§10.1)
    - X-Idempotency-Key on WRITE_IDEMPOTENT_REQUIRED operations (§10.2)
    - Bounded retry with backoff and jitter (§12)
    - Replay/conflict/defer normalization (§17)
    - Proof metadata capture (§16)
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        auth_provider: Optional[AuthProvider] = None,
        user_agent: str = "keyhole-sdk-python",
        session: Optional[requests.Session] = None,
        retry_config: Optional[RetryConfig] = None,
        sdk_version: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_provider = auth_provider
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = self.user_agent
        self.retry_config = retry_config or RetryConfig()
        self.sdk_version = sdk_version

    def execute(
        self,
        method: str,
        path: str,
        *,
        operation_name: str,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> TransportResult:
        """Execute a governed transport request with full identity + retry.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (e.g., "/mcp/v1/runs/start")
            operation_name: Registered operation name for classification
            idempotency_key: Pre-minted key (or auto-generated for writes)
            **kwargs: Passed through to requests (json, params, etc.)

        Returns:
            TransportResult with data, status code, and proof metadata.
        """
        descriptor = get_operation(operation_name)

        # §17.1: Enforce idempotency key requirement
        if descriptor and descriptor.idempotency_required and not idempotency_key:
            idempotency_key = generate_idempotency_key()

        if (
            descriptor
            and descriptor.operation_class == OperationClass.WRITE_IDEMPOTENT_REQUIRED
            and not idempotency_key
        ):
            raise MissingIdempotencyKeyError(
                operation_name,
                request_id="(not yet assigned)",
            )

        # Build proof metadata
        proof = TransportProofMetadata(
            idempotency_key=idempotency_key,
            operation_class=descriptor.operation_class.value if descriptor else "UNREGISTERED",
            command_name=operation_name,
        )

        # Determine retry posture
        retry_policy = (
            descriptor.retry_policy
            if descriptor
            else RetryPolicy.NO_RETRY
        )
        max_attempts = self._max_attempts(retry_policy)

        last_error: Optional[Exception] = None
        last_request_id: str = ""

        for attempt in range(1, max_attempts + 1):
            request_id = generate_request_id()
            last_request_id = request_id

            # Build headers
            headers = dict(kwargs.pop("headers", {}))
            headers["X-Request-Id"] = request_id
            if idempotency_key:
                headers["X-Idempotency-Key"] = idempotency_key
            if self.sdk_version:
                headers["X-Keyhole-SDK-Version"] = self.sdk_version
            if self.auth_provider:
                headers.update(self.auth_provider.get_headers())

            # Record attempt start
            reason = "" if attempt == 1 else f"retry #{attempt - 1}"
            delay_ms = 0
            proof.record_attempt(
                attempt=attempt,
                request_id=request_id,
                reason=reason,
                delay_ms=delay_ms,
            )

            try:
                response = self.session.request(
                    method,
                    f"{self.base_url}{path}",
                    timeout=self.timeout,
                    headers=headers,
                    **kwargs,
                )
            except (requests.ConnectionError, requests.Timeout, OSError) as exc:
                last_error = exc
                # §13: Transport failure after send — unknown outcome
                if attempt < max_attempts and retry_policy != RetryPolicy.NO_RETRY:
                    delay = compute_backoff_delay(attempt, self.retry_config)
                    sleep_for_backoff(delay)
                    continue
                # Final attempt — surface as transport unknown
                proof.mark_observation(ClientObservation.TRANSPORT_UNKNOWN)
                raise TransportUnknownError(
                    f"Transport failure after {attempt} attempt(s): {exc}",
                    request_id=last_request_id,
                    idempotency_key=idempotency_key,
                ) from exc

            # §17.2: Idempotency conflict — stop retrying
            if is_conflict_status(response.status_code):
                proof.mark_observation(ClientObservation.CONFLICT)
                raise IdempotencyConflictError(
                    f"Idempotency conflict (HTTP 409): {response.text[:200]}",
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    server_detail=response.text[:500],
                )

            # §17.4: Rate limit
            if is_rate_limited(response.status_code):
                retry_after = parse_retry_after(response)
                if attempt < max_attempts and retry_policy != RetryPolicy.NO_RETRY:
                    delay = compute_backoff_delay(
                        attempt, self.retry_config, retry_after=retry_after
                    )
                    sleep_for_backoff(delay)
                    continue
                proof.mark_observation(ClientObservation.DEFERRED)
                raise RateLimitedError(
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    retry_after=retry_after,
                )

            # §12.2: Retryable server errors
            if is_retryable_status(response.status_code) and max_attempts > 1:
                retry_after = parse_retry_after(response)
                last_error = RuntimeUnavailableError(
                    f"Runtime returned {response.status_code}"
                )
                if attempt < max_attempts:
                    delay = compute_backoff_delay(
                        attempt, self.retry_config, retry_after=retry_after
                    )
                    sleep_for_backoff(delay)
                    continue
                proof.mark_observation(ClientObservation.TRANSPORT_UNKNOWN)
                raise RetryExhaustedError(
                    f"All {attempt} retry attempts exhausted. "
                    f"Last status: {response.status_code}",
                    request_id=last_request_id,
                    idempotency_key=idempotency_key,
                    attempt_count=attempt,
                    last_error=last_error,
                )

            # Non-retryable 5xx
            if response.status_code >= 500:
                proof.mark_observation(ClientObservation.TRANSPORT_UNKNOWN)
                raise RuntimeUnavailableError(
                    f"Runtime returned {response.status_code}: "
                    f"{response.text[:200]}"
                )

            # §12.3: Client errors (4xx, non-conflict, non-rate-limit)
            if response.status_code >= 400:
                try:
                    body = response.json()
                except ValueError:
                    body = {}
                proof.mark_observation(ClientObservation.NOT_SENT)
                raise PublicEndpointError(
                    body.get("error", response.reason or "request failed"),
                    status_code=response.status_code,
                    detail=body.get("detail", ""),
                )

            # Success path
            try:
                data = response.json()
            except ValueError as exc:
                proof.mark_observation(ClientObservation.EXECUTED)
                raise SchemaError("Response is not valid JSON", raw_data=None) from exc

            # §16.3: Detect replay metadata from server
            server_request_id = response.headers.get("X-Request-Id")
            original_request_id = response.headers.get("X-Original-Request-Id")
            if server_request_id:
                proof.server_request_id = server_request_id
            if original_request_id:
                proof.original_request_id = original_request_id
                proof.mark_observation(ClientObservation.REPLAYED)
            else:
                proof.mark_observation(ClientObservation.EXECUTED)

            return TransportResult(
                data=data,
                status_code=response.status_code,
                proof=proof,
                response_headers=dict(response.headers),
            )

        # Should not reach here, but safety net
        proof.mark_observation(ClientObservation.NOT_SENT)
        raise RetryExhaustedError(
            "All retry attempts exhausted.",
            request_id=last_request_id,
            idempotency_key=idempotency_key,
            attempt_count=max_attempts,
            last_error=last_error,
        )

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def _max_attempts(self, retry_policy: RetryPolicy) -> int:
        """Compute maximum attempts based on retry policy and config."""
        if not self.retry_config.enabled:
            return 1
        if retry_policy == RetryPolicy.NO_RETRY:
            return 1
        return max(1, self.retry_config.max_retries + 1)
