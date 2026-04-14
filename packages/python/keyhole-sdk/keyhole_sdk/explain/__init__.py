"""Governance Explainability and Support Bundles — SDK-CLIENT-20.

Closes the client-side trust layer for governed execution.

Answers: what happened, why did it happen, what did the platform use,
and what should I do next?

Public exports (12 symbols):
  ExplainOutcomeClass        — outcome family enum (9 values)
  RunExplanation             — assembled run explanation model
  RequestInspectionResult    — assembled request inspection model
  SupportBundle              — portable, bounded support artifact
  assemble_run_explanation   — server response → RunExplanation
  assemble_request_inspection — server response → RequestInspectionResult
  assemble_support_bundle    — explanation sources → SupportBundle
  render_explanation         — deterministic human-readable explanation
  render_inspection          — deterministic human-readable inspection
  emit_explain_proof         — write explain artifacts to state dir
  emit_bundle_proof          — write support bundle artifacts to state dir
  map_explain_repair         — repair guidance by error class
"""

from keyhole_sdk.explain.models import (
    ExplainOutcomeClass,
    RunExplanation,
    RequestInspectionResult,
    SupportBundle,
)
from keyhole_sdk.explain.assembler import (
    assemble_run_explanation,
    assemble_request_inspection,
    assemble_support_bundle,
)
from keyhole_sdk.explain.renderer import render_explanation, render_inspection
from keyhole_sdk.explain.proof import emit_explain_proof, emit_bundle_proof
from keyhole_sdk.explain.repair import map_explain_repair

__all__ = [
    "ExplainOutcomeClass",
    "RunExplanation",
    "RequestInspectionResult",
    "SupportBundle",
    "assemble_run_explanation",
    "assemble_request_inspection",
    "assemble_support_bundle",
    "render_explanation",
    "render_inspection",
    "emit_explain_proof",
    "emit_bundle_proof",
    "map_explain_repair",
]
