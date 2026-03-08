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


class StateResponse(BaseModel):
    current_digest: Optional[str] = None
    realized_digests: List[str]
    updated_at: str


class RealizationRequest(BaseModel):
    candidate_digest: str
    payload: Optional[Dict] = None


class RealizationReceipt(BaseModel):
    digest: str
    status: str
    message: str
    realized_at: str
