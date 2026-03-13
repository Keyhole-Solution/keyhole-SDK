"""Governed context retrieval bootstrap — context package.

CE-V5-S42-05: Governed Context Retrieval Bootstrap.

Implements the first context-retrieval flow so the developer kit
can consult governed platform truth through MCP before implementation,
dispatch, or architectural assumption-making.

Public surface:

    ContextClient        — invoke read-only context-access run types
    ContextSnapshot      — normalized local representation of retrieved context
    TopologyInfo         — platform shape and governance model
    ContractInfo         — MCP contract and schema posture
    InterfaceInfo        — participant-relevant interface endpoints
    ContextAccessInfo    — implemented context-access surfaces
    GuidanceInfo         — participant guidance slice
    RetrievalMetadata    — retrieval metadata (digest, timestamps, etc.)
    RunStartRequest      — request shape for POST /mcp/v1/runs/start
    RunStartResponse     — raw response from a run-start invocation
"""

from keyhole_sdk.context.models import (
    ContextAccessInfo,
    ContextSnapshot,
    ContractInfo,
    GuidanceInfo,
    InterfaceInfo,
    RetrievalMetadata,
    RunStartRequest,
    RunStartResponse,
    TopologyInfo,
)
from keyhole_sdk.context.client import ContextClient

__all__ = [
    "ContextClient",
    "ContextSnapshot",
    "TopologyInfo",
    "ContractInfo",
    "InterfaceInfo",
    "ContextAccessInfo",
    "GuidanceInfo",
    "RetrievalMetadata",
    "RunStartRequest",
    "RunStartResponse",
]
