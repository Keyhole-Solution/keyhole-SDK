"""Governed run dispatch — SDK-CLIENT-09.

Provides request construction, preflight validation, proof emission,
outcome rendering, and repair guidance for ``keyhole run``.
"""

from keyhole_sdk.run_dispatch.preflight import RunPreflight, PreflightFailure
from keyhole_sdk.run_dispatch.request_builder import (
    RunRequest,
    build_run_request,
)
from keyhole_sdk.run_dispatch.dispatcher import (
    RunOutcome,
    OutcomeStatus,
    dispatch_run,
)
from keyhole_sdk.run_dispatch.proof_emitter import emit_run_proof
from keyhole_sdk.run_dispatch.repair import map_repair_guidance

__all__ = [
    "RunPreflight",
    "PreflightFailure",
    "RunRequest",
    "build_run_request",
    "RunOutcome",
    "OutcomeStatus",
    "dispatch_run",
    "emit_run_proof",
    "map_repair_guidance",
]
