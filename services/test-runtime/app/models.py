from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class IdentityResponse(BaseModel):
    runtime_id: str
    runtime_name: str
    runtime_version: str
    environment: str
    capabilities: List[str]
    governance_mode: str


class ModeResponse(BaseModel):
    mode: str
    mcp_configured: bool
    auditable_upstream: bool
    evidence_disclaimer: str


class StateResponse(BaseModel):
    current_digest: Optional[str] = None
    realized_digests: List[str]
    updated_at: str


class ContractResponse(BaseModel):
    contract_version: str
    surface_version: str
    supported_modes: List[str]
    startup_methods: List[str]
    runtime_interfaces: Dict[str, Any]
    identity_contract: Dict[str, Any]
    state_contract: Dict[str, Any]
    realize_contract: Dict[str, Any]
    mode_contract: Dict[str, Any]
    bridge_law_reference: str
    public_safety_note: str


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
    message: str
    realized_at: str
