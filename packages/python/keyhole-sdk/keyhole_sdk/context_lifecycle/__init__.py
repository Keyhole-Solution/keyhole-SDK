"""Context lifecycle management — SDK-CLIENT-16.

Makes governed context a first-class, builder-visible execution boundary.

Public surface:

    ContextCompileRequest     — deterministic compile request shape
    build_compile_request     — factory for compile requests
    ContextCompileResult      — result from a context compile
    compile_context           — dispatch context.compile through GovernedTransport
    ContextInspectResult      — result from context inspect
    inspect_context           — retrieve and render context for a digest
    ContextPreflight          — preflight gate for context commands
    ContextPreflightFailure   — describes why preflight blocked
    emit_context_proof        — write context proof artifacts
    emit_context_binding_proof — write context-binding proof for runs
    map_context_repair        — map context errors to repair guidance
    validate_digest           — validate digest format
    LocalContextTracker       — track most recently compiled digest
"""

from keyhole_sdk.context_lifecycle.compile import (
    ContextCompileRequest,
    ContextCompileResult,
    build_compile_request,
    compile_context,
)
from keyhole_sdk.context_lifecycle.inspect import (
    ContextInspectResult,
    inspect_context,
)
from keyhole_sdk.context_lifecycle.preflight import (
    ContextPreflight,
    ContextPreflightFailure,
)
from keyhole_sdk.context_lifecycle.proof import (
    emit_context_proof,
    emit_context_binding_proof,
)
from keyhole_sdk.context_lifecycle.repair import map_context_repair
from keyhole_sdk.context_lifecycle.digest import validate_digest
from keyhole_sdk.context_lifecycle.tracker import LocalContextTracker

__all__ = [
    "ContextCompileRequest",
    "ContextCompileResult",
    "build_compile_request",
    "compile_context",
    "ContextInspectResult",
    "inspect_context",
    "ContextPreflight",
    "ContextPreflightFailure",
    "emit_context_proof",
    "emit_context_binding_proof",
    "map_context_repair",
    "validate_digest",
    "LocalContextTracker",
]
