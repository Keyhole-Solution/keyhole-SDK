"""Grouped client surfaces — clean public mental model.

Per §11: Recommended grouped client surfaces:
  system, identity, declarations, runs, evidence
"""

from keyhole_sdk.surfaces.system import SystemSurface
from keyhole_sdk.surfaces.identity import IdentitySurface
from keyhole_sdk.surfaces.declarations import DeclarationsSurface
from keyhole_sdk.surfaces.runs import RunsSurface
from keyhole_sdk.surfaces.evidence import EvidenceSurface

__all__ = [
    "SystemSurface",
    "IdentitySurface",
    "DeclarationsSurface",
    "RunsSurface",
    "EvidenceSurface",
]
