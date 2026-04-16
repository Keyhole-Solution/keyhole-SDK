"""SDK-CLIENT-22 — Deregistration models.

Typed request/response models for the account deletion lifecycle.
Dispatches through ``auth.remove`` via ``POST /mcp/v1/runs/start``.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class DeregistrationStatus(str, enum.Enum):
    """Outcome status families for a deregistration attempt (§14)."""

    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REPLAYED = "replayed"
    REJECTED = "rejected"
    ALREADY_DELETED = "already_deleted"
    FAILED = "failed"
    TRANSPORT_ERROR = "transport_error"


class DeregistrationRequest(BaseModel):
    """Client-side deletion request — §13.

    Serialises to the governed run payload for ``auth.remove``.
    """

    registration_id: str
    confirm: bool = True
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    realm: str = "kh-prod"

    def to_run_payload(self) -> Dict[str, Any]:
        """Wire format for ``POST /mcp/v1/runs/start``."""
        return {
            "run_type": "auth.remove",
            "parameters": {
                "user_id": self.registration_id,
                "realm": self.realm,
                "confirm": self.confirm,
            },
        }

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialisation (no secrets)."""
        return {
            "registration_id": self.registration_id,
            "realm": self.realm,
            "confirm": self.confirm,
            "correlation_id": self.correlation_id,
        }


class DeregistrationOutcome(BaseModel):
    """Result of a deregistration dispatch — §15, §18."""

    status: DeregistrationStatus
    registration_id: str
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    reason: Optional[str] = None
    repair_guidance: List[str] = Field(default_factory=list)
    proof_path: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _normalise_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Map server ``removed: true`` → ACCEPTED
            if values.get("removed") is True and "status" not in values:
                values["status"] = DeregistrationStatus.ACCEPTED
            # Map ``lifecycle_state: removed`` → ACCEPTED
            if values.get("lifecycle_state") == "removed" and "status" not in values:
                values["status"] = DeregistrationStatus.ACCEPTED
            # Map ``identity_not_found`` → ALREADY_DELETED
            err = values.get("error") or ""
            if "identity_not_found" in str(err).lower() and "status" not in values:
                values["status"] = DeregistrationStatus.ALREADY_DELETED
        return values

    def safe_summary(self) -> Dict[str, Any]:
        """Proof-safe summary for artifact emission."""
        return {
            "status": self.status.value,
            "registration_id": self.registration_id,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "reason": self.reason,
            "repair_guidance": self.repair_guidance,
        }
