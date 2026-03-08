import os

from fastapi import APIRouter

from .models import (
    HealthResponse,
    IdentityResponse,
    RealizationReceipt,
    RealizationRequest,
    StateResponse,
)
from .state import runtime_state

router = APIRouter()

RUNTIME_VERSION = os.environ.get("RUNTIME_VERSION", "0.1.0")
RUNTIME_ENVIRONMENT = os.environ.get("RUNTIME_ENVIRONMENT", "development")


@router.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


@router.get("/identity", response_model=IdentityResponse)
async def identity():
    return IdentityResponse(
        runtime_id="keyhole-test-runtime",
        runtime_name="Keyhole Test Runtime",
        runtime_version=RUNTIME_VERSION,
        environment=RUNTIME_ENVIRONMENT,
        capabilities=["realize", "state", "health"],
    )


@router.get("/state", response_model=StateResponse)
async def state():
    return StateResponse(**runtime_state.get_state())


@router.post("/realize", response_model=RealizationReceipt)
async def realize(request: RealizationRequest):
    receipt = runtime_state.apply_digest(request.candidate_digest)
    return RealizationReceipt(**receipt)
