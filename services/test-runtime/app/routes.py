import os

from fastapi import APIRouter, HTTPException

from .bridge import governance_check, governance_mode
from .models import (
    HealthResponse,
    IdentityResponse,
    RealizationReceipt,
    RealizationRequest,
    StateResponse,
)
from .state import RUNTIME_VERSION, runtime_state

router = APIRouter()

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
        governance_mode=governance_mode(),
    )


@router.get("/state", response_model=StateResponse)
async def state():
    return StateResponse(**runtime_state.get_state())


@router.post("/realize", response_model=RealizationReceipt)
async def realize(request: RealizationRequest):
    # Gate every realization request through Keyhole governance before
    # applying any local mutation.  When KEYHOLE_MCP_URL is configured this
    # calls the real MCP governance controller; otherwise it runs in
    # local-only mode (for initial SDK / tooling development only).
    verdict = await governance_check(
        candidate_digest=request.candidate_digest,
        payload=dict(request.payload),
    )

    if not verdict["ok"]:
        raise HTTPException(
            status_code=422,
            detail={
                "verdict": verdict["verdict"],
                "reason": verdict["reason"],
                "candidate_digest": request.candidate_digest,
            },
        )

    receipt = runtime_state.apply_digest(
        digest=request.candidate_digest,
        governance_verdict=verdict["verdict"],
        governance_reason=verdict.get("reason", ""),
    )
    return RealizationReceipt(**receipt)
