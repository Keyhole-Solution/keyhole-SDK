"""Schema discovery helpers.

CE-V5-S42-06: Run-Type Safety & Schema Discovery Helpers.

Provides schema hints and request-shape guidance for known run types.
When schema information is unavailable, returns an explicit
"schema unavailable — re-discover first" posture.

Must never:
  - fabricate schema when discovery is unavailable
  - guess parameter structures from naming convention
  - depend on private platform source
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.dispatch.models import SchemaHint


# ── Known request schemas ───────────────────────────────────
# Static schema hints for currently implemented run types.
# These reflect the published request shape for POST /mcp/v1/runs/start.
# The envelope is always {"run_type": "...", "params": {...}}.

_KNOWN_SCHEMAS: Dict[str, SchemaHint] = {
    "context.compile": SchemaHint(
        run_type="context.compile",
        available=True,
        required_params=[],
        optional_params=[],
        example={"run_type": "context.compile", "params": {}},
        notes="Primary context bootstrap surface. No required parameters.",
    ),
    "gaps.list": SchemaHint(
        run_type="gaps.list",
        available=True,
        required_params=[],
        optional_params=[],
        example={"run_type": "gaps.list", "params": {}},
        notes="Browse current gaps. No required parameters.",
    ),
    "gaps.status": SchemaHint(
        run_type="gaps.status",
        available=True,
        required_params=[],
        optional_params=[],
        example={"run_type": "gaps.status", "params": {}},
        notes="Current gap status posture.",
    ),
    "gaps.next_open_canonical": SchemaHint(
        run_type="gaps.next_open_canonical",
        available=True,
        required_params=[],
        optional_params=[],
        example={"run_type": "gaps.next_open_canonical", "params": {}},
        notes="Next open canonical gap.",
    ),
    "lineage.get.v0_1": SchemaHint(
        run_type="lineage.get.v0_1",
        available=True,
        required_params=["target"],
        optional_params=[],
        example={
            "run_type": "lineage.get.v0_1",
            "params": {"target": "<target-identifier>"},
        },
        notes="Causal lineage for a specific target. Requires 'target' parameter.",
    ),
    "convergence.status.v0_1": SchemaHint(
        run_type="convergence.status.v0_1",
        available=True,
        required_params=[],
        optional_params=[],
        example={"run_type": "convergence.status.v0_1", "params": {}},
        notes="Current convergence posture. No required parameters.",
    ),
}


class SchemaHelper:
    """Schema discovery helper for run-type request shapes.

    Provides schema hints for known run types.  When a run type is
    not recognized, returns an explicit "unavailable" hint directing
    the participant to re-discover.

    Usage::

        helper = SchemaHelper()
        hint = helper.get_hint("lineage.get.v0_1")
        assert hint.available
        assert "target" in hint.required_params

    With capabilities::

        caps = client.fetch()
        helper = SchemaHelper.from_capabilities(caps)
        hint = helper.get_hint("context.compile")
    """

    def __init__(
        self,
        *,
        schemas: Optional[Dict[str, SchemaHint]] = None,
    ) -> None:
        self._schemas: Dict[str, SchemaHint] = dict(
            schemas if schemas is not None else _KNOWN_SCHEMAS
        )

    @classmethod
    def from_capabilities(cls, capabilities_result: object) -> "SchemaHelper":
        """Build a schema helper enriched with capabilities guidance.

        Incorporates implemented surfaces from the capabilities
        response as run types with known (possibly empty) schemas.
        """
        schemas = dict(_KNOWN_SCHEMAS)

        surfaces = getattr(
            getattr(capabilities_result, "context_access", None),
            "implemented_surfaces",
            [],
        )
        if isinstance(surfaces, list):
            for s in surfaces:
                if isinstance(s, str) and s and s not in schemas:
                    schemas[s] = SchemaHint(
                        run_type=s,
                        available=True,
                        notes=(
                            f"Discovered via capabilities. "
                            f"Consult schema discovery for parameter details."
                        ),
                    )

        return cls(schemas=schemas)

    def get_hint(self, run_type: str) -> SchemaHint:
        """Return schema guidance for a run type.

        Returns a hint with ``available=True`` for known run types,
        or a hint with ``available=False`` and guidance to re-discover
        for unknown run types.
        """
        if run_type in self._schemas:
            return self._schemas[run_type]

        return SchemaHint(
            run_type=run_type,
            available=False,
            notes=(
                f"No schema available for '{run_type}'. "
                "Re-discover via GET /mcp/v1/capabilities or "
                "consult published guidance before assuming request shape."
            ),
        )

    def validate_params(
        self,
        run_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Check params against known schema.

        Returns a list of warning strings.  An empty list means no
        issues were detected.  This does not guarantee server
        acceptance — it catches obvious participant-side mistakes.
        """
        warnings: List[str] = []
        hint = self.get_hint(run_type)

        if not hint.available:
            warnings.append(
                f"Schema unavailable for '{run_type}'. "
                "Cannot validate parameters. Re-discover first."
            )
            return warnings

        actual_params = params or {}

        # Check required params
        for req in hint.required_params:
            if req not in actual_params:
                warnings.append(
                    f"Required parameter '{req}' is missing for '{run_type}'."
                )

        return warnings

    @property
    def known_run_types(self) -> List[str]:
        """Return sorted list of run types with known schemas."""
        return sorted(self._schemas.keys())
