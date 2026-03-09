from typing import Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class IdentityResponse(BaseModel):
    runtime_id: str
    runtime_name: str
    runtime_version: str
    environment: str
    capabilities: List[str]
    governance_mode: str = "local-only"  # "governed" | "local-only" | "misconfigured"


class StateResponse(BaseModel):
    current_digest: Optional[str] = None
    realized_digests: List[str]
    updated_at: str


class RealizationRequest(BaseModel):
    """Accepts both the simple SDK form and the full bridge envelope.

    Simple form (SDK/CLI):
        {"candidate_digest": "sha256:...", "payload": {}}

    Bridge envelope (reference bridge):
        {"candidate_digest": "sha256:...", "promotion_uuid": "...",
         "artifact_refs": [...], "expected_capabilities": [...],
         "lane": "prod", "purpose": "production"}
    """

    candidate_digest: str
    payload: Optional[Dict] = None
    # Bridge envelope fields (optional — present when called by reference bridge)
    promotion_uuid: Optional[str] = None
    artifact_refs: Optional[List[str]] = None
    expected_capabilities: Optional[List[str]] = None
    lane: Optional[str] = None
    purpose: Optional[str] = None


class RealizationReceipt(BaseModel):
    digest: str
    status: str
    result: str  # Same value as status — used by the reference bridge
    message: str
    realized_at: str
    governance_verdict: str = "LOCAL_ONLY"
    version: str = ""  # Runtime version at time of realization
    pointer: str = ""  # Local pointer state after realization
