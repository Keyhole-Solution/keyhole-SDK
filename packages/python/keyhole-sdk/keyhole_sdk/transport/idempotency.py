"""Idempotency key generation and attempt-identity tracking.

SDK-CLIENT-15 §10-§11: Request identity and operation-attempt identity.

Key rules:
  - Every request gets a fresh X-Request-Id (UUIDv4)
  - Every WRITE_IDEMPOTENT_REQUIRED attempt gets a fresh X-Idempotency-Key
  - Retries of the same attempt reuse the same idempotency key
  - Different attempts mint different keys even for identical payloads
  - Payload hashing must NOT be the sole key generation rule
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def generate_request_id() -> str:
    """Generate a fresh request ID (UUIDv4). §11.1."""
    return str(uuid.uuid4())


def generate_idempotency_key() -> str:
    """Generate a fresh idempotency key (UUIDv4). §11.2."""
    return str(uuid.uuid4())


@dataclass
class OperationAttempt:
    """Tracks a single logical write attempt across retries.

    §8.3: Same attempt, same key — retries preserve identity.
    §8.4: Different attempt, different key — intentional re-submit mints fresh.
    """

    operation_name: str
    idempotency_key: str = field(default_factory=generate_idempotency_key)
    attempt_number: int = 0
    created_at: str = field(default="")
    request_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def next_request_id(self) -> str:
        """Mint a fresh request ID for the next retry within this attempt."""
        self.attempt_number += 1
        rid = generate_request_id()
        self.request_ids.append(rid)
        return rid

    def to_dict(self) -> dict:
        """Serialize attempt tracking state."""
        return {
            "operation_name": self.operation_name,
            "idempotency_key": self.idempotency_key,
            "attempt_number": self.attempt_number,
            "created_at": self.created_at,
            "request_ids": list(self.request_ids),
        }
