"""Replay-aware proof metadata for transport operations.

SDK-CLIENT-15 §16: Client-side proof artifacts for write-bearing
operations must include replay-relevant transport metadata.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ClientObservation(enum.Enum):
    """Final client observation of operation outcome. §16.2."""

    EXECUTED = "executed"
    REPLAYED = "replayed"
    DEFERRED = "deferred"
    CONFLICT = "conflict"
    TRANSPORT_UNKNOWN = "transport_unknown"
    NOT_SENT = "not_sent"


@dataclass
class AttemptMetadata:
    """Per-attempt timing and identity for proof. §16.1."""

    attempt: int
    request_id: str
    timestamp: str
    reason: str = ""
    delay_ms: int = 0


@dataclass
class TransportProofMetadata:
    """Proof-core metadata for a transport operation. §16.1.

    Fields:
      - request_id: last request ID used
      - idempotency_key: operation-attempt identity (if applicable)
      - operation_class: classified operation type
      - command_name: CLI or SDK command name
      - attempt_count: total attempts made
      - final_client_observation: what the client observed
      - server_request_id: server-issued correlation ID (if returned)
      - original_request_id: original request ID from replay metadata
      - attempts: per-attempt records
      - retry_reasons: textual reasons for each retry
    """

    request_id: str = ""
    idempotency_key: Optional[str] = None
    operation_class: str = ""
    command_name: str = ""
    attempt_count: int = 0
    final_client_observation: ClientObservation = ClientObservation.NOT_SENT
    server_request_id: Optional[str] = None
    original_request_id: Optional[str] = None
    attempts: List[AttemptMetadata] = field(default_factory=list)
    retry_reasons: List[str] = field(default_factory=list)

    def record_attempt(
        self,
        attempt: int,
        request_id: str,
        reason: str = "",
        delay_ms: int = 0,
    ) -> None:
        """Record a single attempt in the proof trail."""
        self.attempts.append(
            AttemptMetadata(
                attempt=attempt,
                request_id=request_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=reason,
                delay_ms=delay_ms,
            )
        )
        self.attempt_count = len(self.attempts)
        self.request_id = request_id
        if reason:
            self.retry_reasons.append(reason)

    def mark_observation(self, observation: ClientObservation) -> None:
        """Set the final client observation."""
        self.final_client_observation = observation

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to proof-core dict. §16.4: hot core."""
        return {
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "operation_class": self.operation_class,
            "command_name": self.command_name,
            "attempt_count": self.attempt_count,
            "final_client_observation": self.final_client_observation.value,
            "server_request_id": self.server_request_id,
            "original_request_id": self.original_request_id,
            "attempts": [
                {
                    "attempt": a.attempt,
                    "request_id": a.request_id,
                    "timestamp": a.timestamp,
                    "reason": a.reason,
                    "delay_ms": a.delay_ms,
                }
                for a in self.attempts
            ],
            "retry_reasons": list(self.retry_reasons),
        }
