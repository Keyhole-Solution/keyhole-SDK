"""Runtime contract proof emitter — SDK-CLIENT-24 §10.5 §16.

Writes deterministic proof artifacts for runtime contract operations to a
tool-owned state directory. Default location:
``<state_dir>/runtime-contract/<correlation-id>/``.

Artifacts emitted (when relevant):
  - ``request.json``                — outbound runtime context payload
  - ``response.json``               — raw server response
  - ``runtime-context.json``        — typed runtime context
  - ``runtime-diagnostics.json``    — local diagnostics snapshot
  - ``surface.json``                — runtime surface result
  - ``compatibility-result.json``   — typed compatibility result
  - ``repair.json``                 — server (and fallback) repair guidance
  - ``correlation.json``            — request/run identity correlation
  - ``summary.md``                  — human-readable summary
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from keyhole_sdk.runtime_contract.models import (
    RuntimeCompatibilityResult,
    RuntimeContext,
    RuntimeDiagnostics,
    RuntimeProofArtifact,
    RuntimeSurfaceResult,
)


def _default_state_dir() -> Path:
    """Tool-owned state root under the user's home directory."""
    return Path.home() / ".keyhole" / "state"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


class RuntimeContractProofEmitter:
    """Emit runtime contract proof artifacts to a tool-owned state dir."""

    def __init__(self, state_dir: Optional[Path] = None) -> None:
        self.state_dir = Path(state_dir) if state_dir else _default_state_dir()

    def bundle_dir(self, correlation_id: str) -> Path:
        return self.state_dir / "runtime-contract" / correlation_id

    def emit(
        self,
        *,
        correlation_id: str,
        request_payload: Optional[Dict[str, Any]] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        runtime_context: Optional[RuntimeContext] = None,
        diagnostics: Optional[RuntimeDiagnostics] = None,
        surface: Optional[RuntimeSurfaceResult] = None,
        compatibility: Optional[RuntimeCompatibilityResult] = None,
        command: str = "",
    ) -> RuntimeProofArtifact:
        """Write proof artifacts for one runtime contract operation."""
        if not correlation_id:
            correlation_id = "uncorrelated-" + datetime.now(
                timezone.utc
            ).strftime("%Y%m%dT%H%M%SZ")

        bundle = self.bundle_dir(correlation_id)
        bundle.mkdir(parents=True, exist_ok=True)
        files: List[str] = []

        if request_payload is not None:
            _write_json(bundle / "request.json", request_payload)
            files.append("request.json")

        if response_payload is not None:
            _write_json(bundle / "response.json", response_payload)
            files.append("response.json")

        if runtime_context is not None:
            _write_json(bundle / "runtime-context.json", runtime_context.to_payload())
            files.append("runtime-context.json")

        if diagnostics is not None:
            _write_json(bundle / "runtime-diagnostics.json", diagnostics.to_dict())
            files.append("runtime-diagnostics.json")

        if surface is not None:
            _write_json(bundle / "surface.json", surface.to_dict())
            files.append("surface.json")

        if compatibility is not None:
            _write_json(
                bundle / "compatibility-result.json", compatibility.to_dict()
            )
            files.append("compatibility-result.json")
            _write_json(bundle / "repair.json", compatibility.repair.to_dict())
            files.append("repair.json")

        _write_json(
            bundle / "correlation.json",
            {
                "correlation_id": correlation_id,
                "command": command,
                "emitted_at": _now_iso(),
            },
        )
        files.append("correlation.json")

        summary_lines = ["# Runtime Contract Operation", ""]
        summary_lines.append(f"correlation_id: {correlation_id}")
        if command:
            summary_lines.append(f"command: {command}")
        summary_lines.append(f"emitted_at: {_now_iso()}")
        if surface is not None:
            summary_lines.append("")
            summary_lines.append("## Surface")
            summary_lines.append(f"status: {surface.status}")
            summary_lines.append(
                f"contract_version: {surface.contract_version}"
            )
        if compatibility is not None:
            summary_lines.append("")
            summary_lines.append("## Compatibility")
            summary_lines.append(f"status: {compatibility.status.value}")
            if compatibility.selected_profile:
                summary_lines.append(
                    f"selected_profile: {compatibility.selected_profile}"
                )
            if compatibility.runtime_trust_level:
                summary_lines.append(
                    f"runtime_trust_level: "
                    f"{compatibility.runtime_trust_level.value}"
                )
            if compatibility.reason:
                summary_lines.append(f"reason: {compatibility.reason}")
        (bundle / "summary.md").write_text(
            "\n".join(summary_lines) + "\n", encoding="utf-8"
        )
        files.append("summary.md")

        return RuntimeProofArtifact(
            correlation_id=correlation_id,
            bundle_dir=str(bundle),
            files=files,
        )
