"""Surface negotiation SDK-CLIENT-21 — public package exports.

Provides the full surface negotiation layer:
  - NegotiationResult      — §11 normalized negotiation artifact
  - NegotiatedFeatures     — §11 feature presence map
  - SurfaceClass           — §8 required / optional / transitional
  - NegotiationStatus      — §11 compatible / degraded / blocked
  - CommandCompatibilityResult — §16 per-command evaluation result
  - CommandStatus          — §16 allowed / degraded / blocked
  - SurfaceEntry           — classified surface with presence info
  - SURFACE_TAXONOMY       — §8 taxonomy dict
  - COMMAND_REQUIREMENTS   — §16 command surface registry
  - classify_surfaces()    — §11 surface classification
  - negotiate()            — §9 §11 full negotiation from CapabilitiesResult
  - negotiate_from_raw()   — convenience wrapper for raw dict
  - evaluate_command()     — §16 per-command compatibility check
  - evaluate_all_commands() — §16 bulk evaluation
  - write_negotiation_artifacts() — §12 artifact writer
  - map_negotiation_repair()      — §14 §15 repair guidance
"""

from keyhole_sdk.negotiation.models import (  # noqa: F401
    CompatibilitySummary,
    CommandCompatibilityResult,
    CommandStatus,
    NegotiatedFeatures,
    NegotiationResult,
    NegotiationStatus,
    SurfaceClass,
    SurfaceEntry,
)

from keyhole_sdk.negotiation.classifier import (  # noqa: F401
    SURFACE_TAXONOMY,
    classify_surfaces,
)

from keyhole_sdk.negotiation.evaluator import (  # noqa: F401
    COMMAND_REQUIREMENTS,
    COMMAND_OPTIONAL_SURFACES,
    evaluate_command,
    evaluate_all_commands,
)

from keyhole_sdk.negotiation.negotiator import (  # noqa: F401
    negotiate,
    negotiate_from_raw,
)

from keyhole_sdk.negotiation.artifact import write_negotiation_artifacts  # noqa: F401

from keyhole_sdk.negotiation.repair import map_negotiation_repair  # noqa: F401

__all__ = [
    # Models
    "CompatibilitySummary",
    "CommandCompatibilityResult",
    "CommandStatus",
    "NegotiatedFeatures",
    "NegotiationResult",
    "NegotiationStatus",
    "SurfaceClass",
    "SurfaceEntry",
    # Classifier
    "SURFACE_TAXONOMY",
    "classify_surfaces",
    # Evaluator
    "COMMAND_REQUIREMENTS",
    "COMMAND_OPTIONAL_SURFACES",
    "evaluate_command",
    "evaluate_all_commands",
    # Negotiator
    "negotiate",
    "negotiate_from_raw",
    # Artifact
    "write_negotiation_artifacts",
    # Repair
    "map_negotiation_repair",
]
