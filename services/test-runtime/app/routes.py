import os

from fastapi import APIRouter, HTTPException

from .bridge import governance_check
from .contract import RUNTIME_BRIDGE_CONTRACT
from .mode import resolve_mode
from .models import (
    ContractResponse,
    HealthResponse,
    IdentityResponse,
    ModeResponse,
    RealizationReceipt,
    RealizationRequest,
    StateResponse,
)
from .state import RUNTIME_VERSION, runtime_state

router = APIRouter()

RUNTIME_ENVIRONMENT = os.environ.get("RUNTIME_ENVIRONMENT", "dev")


@router.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


@router.get("/identity", response_model=IdentityResponse)
async def identity():
    mode_status = resolve_mode()
    return IdentityResponse(
        runtime_id="keyhole-test-runtime",
        runtime_name="Keyhole Test Runtime",
        runtime_version=RUNTIME_VERSION,
        environment=RUNTIME_ENVIRONMENT,
        capabilities=["realize", "state", "health"],
        governance_mode=mode_status.mode,
    )


@router.get("/mode", response_model=ModeResponse)
async def mode():
    ms = resolve_mode()
    return ModeResponse(
        mode=ms.mode,
        mcp_configured=ms.mcp_configured,
        auditable_upstream=ms.auditable_upstream,
        evidence_disclaimer=ms.evidence_disclaimer,
    )


@router.get("/contract", response_model=ContractResponse)
async def contract():
    return ContractResponse(**RUNTIME_BRIDGE_CONTRACT)


@router.get("/state", response_model=StateResponse)
async def state():
    return StateResponse(**runtime_state.get_state())


@router.post("/realize", response_model=RealizationReceipt)
async def realize(request: RealizationRequest):
    # Gate every realization request through Keyhole governance before
    # applying any local mutation.  When KEYHOLE_MCP_URL is configured this
    # calls the real MCP governance controller; otherwise it runs in
    # local-only mode (for initial SDK / tooling development only).
    mode_status = resolve_mode()
    if request.require_governed and mode_status.mode != "governed":
        raise HTTPException(
            status_code=412,
            detail={
                "verdict": "REJECT",
                "reason": (
                    "Governed realization requested, but KEYHOLE_MCP_URL and "
                    "KEYHOLE_MCP_TOKEN are not both configured."
                ),
                "candidate_digest": request.candidate_digest,
                "governed": False,
                "event_spine_evidence": False,
            },
        )

    payload = dict(request.payload or {})
    if request.local_invariant_result:
        payload["local_invariant_result"] = request.local_invariant_result
    if request.governance_context_id:
        payload["governance_context_id"] = request.governance_context_id
    if request.passport_digest:
        payload["passport_digest"] = request.passport_digest
    if request.trust_digest:
        payload["trust_digest"] = request.trust_digest

    verdict = await governance_check(
        candidate_digest=request.candidate_digest,
        payload=payload,
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

    governance_receipt = verdict.get("governance_receipt", {})
    if request.require_governed:
        missing = [
            name
            for name in (
                "governance_verdict",
                "drift_state",
                "governance_context_id",
                "mcp_event_id",
            )
            if not governance_receipt.get(name)
        ]
        if missing or not governance_receipt.get("event_spine_evidence"):
            raise HTTPException(
                status_code=502,
                detail={
                    "verdict": "REJECT",
                    "reason": (
                        "Governed realization approved by MCP but missing required "
                        "upstream evidence fields: " + ", ".join(missing or ["event_spine_evidence"])
                    ),
                    "candidate_digest": request.candidate_digest,
                    "governed": False,
                    "event_spine_evidence": False,
                },
            )
    receipt = runtime_state.apply_digest(
        digest=request.candidate_digest,
        governance_verdict=str(
            governance_receipt.get("governance_verdict") or verdict["verdict"]
        ),
        governance_reason=verdict.get("reason", ""),
        governed=bool(governance_receipt.get("governed", False)),
        event_spine_evidence=bool(governance_receipt.get("event_spine_evidence", False)),
        governance_context_id=(
            governance_receipt.get("governance_context_id")
            or request.governance_context_id
            or ""
        ),
        drift_state=str(governance_receipt.get("drift_state") or ""),
        mcp_event_id=str(governance_receipt.get("mcp_event_id") or ""),
        proof_id=str(governance_receipt.get("proof_id") or ""),
        receipt_id=str(governance_receipt.get("receipt_id") or ""),
        passport_digest=request.passport_digest or "",
        trust_digest=request.trust_digest or "",
    )
    return RealizationReceipt(**receipt)
