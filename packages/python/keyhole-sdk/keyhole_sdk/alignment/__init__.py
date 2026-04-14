"""Alignment Guidance — SDK-CLIENT-11.

Turns repo analysis results into actionable, deterministic guidance.

Provides:
  - GuidanceItem / GuidanceClass / GuidanceSeverity / GuidanceState
  - AlignmentReadiness
  - AlignmentGuidanceRequest / AlignmentGuidanceResult
  - render_guidance()        — deterministic ranking + rendering
  - submit_alignment()       — MCP boundary submission (accepted/deferred-aware)
  - emit_alignment_proof()   — writes proof bundle to tool-owned state dir
  - map_alignment_repair()   — repair guidance for failure classes
"""

from keyhole_sdk.alignment.models import (
    AlignmentGuidanceRequest,
    AlignmentGuidanceResult,
    AlignmentReadiness,
    GuidanceClass,
    GuidanceItem,
    GuidanceSeverity,
    GuidanceState,
)
from keyhole_sdk.alignment.ranker import render_guidance
from keyhole_sdk.alignment.submitter import submit_alignment
from keyhole_sdk.alignment.proof import emit_alignment_proof
from keyhole_sdk.alignment.repair import map_alignment_repair

__all__ = [
    # Models
    "AlignmentGuidanceRequest",
    "AlignmentGuidanceResult",
    "AlignmentReadiness",
    "GuidanceClass",
    "GuidanceItem",
    "GuidanceSeverity",
    "GuidanceState",
    # Core functions
    "render_guidance",
    "submit_alignment",
    "emit_alignment_proof",
    "map_alignment_repair",
]
