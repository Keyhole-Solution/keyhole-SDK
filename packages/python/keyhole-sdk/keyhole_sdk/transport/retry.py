"""Bounded retry with exponential backoff, jitter, and Retry-After.

SDK-CLIENT-15 §12: Retry Rules.

Key rules:
  - Retry is not blind resend
  - Bounded retry budget (no unbounded loops)
  - Exponential backoff with jitter
  - Respect Retry-After header
  - Same idempotency key preserved across retries
  - Distinguish safe vs unsafe retry conditions
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from keyhole_sdk.transport.errors import (
    DeferredError,
    IdempotencyConflictError,
    RateLimitedError,
    RetryExhaustedError,
    TransportUnknownError,
)


@dataclass(frozen=True)
class RetryConfig:
    """Transport retry configuration per §20."""

    enabled: bool = True
    max_retries: int = 3
    backoff_base_ms: int = 250
    backoff_max_ms: int = 5000
    respect_retry_after: bool = True
    jitter: bool = True


@dataclass
class RetryAttemptRecord:
    """Record of a single retry attempt for proof metadata."""

    attempt: int
    request_id: str
    timestamp: str
    reason: str
    delay_ms: int = 0


def compute_backoff_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: Optional[float] = None,
) -> float:
    """Compute delay in seconds for the given attempt number.

    §12.5: Bounded exponential backoff with jitter.
    §12.6: Respect Retry-After.
    """
    # If server says Retry-After, respect that as a floor
    if retry_after is not None and config.respect_retry_after:
        return max(retry_after, 0.0)

    # Exponential backoff in ms
    base_ms = config.backoff_base_ms * (2 ** (attempt - 1))
    capped_ms = min(base_ms, config.backoff_max_ms)

    # Jitter: uniform random between 0 and capped delay
    if config.jitter:
        delay_ms = random.uniform(0, capped_ms)
    else:
        delay_ms = float(capped_ms)

    return delay_ms / 1000.0


def is_retryable_status(status_code: int) -> bool:
    """Determine if an HTTP status code is safe for automatic retry.

    §12.2: Safe automatic retry conditions.
    """
    return status_code in {
        408,  # Request Timeout
        429,  # Too Many Requests (rate limit)
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }


def is_conflict_status(status_code: int) -> bool:
    """Determine if the status indicates an idempotency conflict.

    §12.3: Do not auto-retry conflicts.
    """
    return status_code == 409


def is_rate_limited(status_code: int) -> bool:
    """Determine if the server is rate-limiting."""
    return status_code == 429


def parse_retry_after(response: requests.Response) -> Optional[float]:
    """Extract Retry-After delay in seconds from response headers.

    §12.6: When the server provides Retry-After, respect it.
    """
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def sleep_for_backoff(delay: float) -> None:
    """Sleep for the computed backoff delay. Extracted for testability."""
    if delay > 0:
        time.sleep(delay)
