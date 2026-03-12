"""System surface — health and compatibility operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from keyhole_sdk import __version__
from keyhole_sdk.exceptions import (
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.models import (
    CompatibilityResult,
    CompatibilityStatus,
    RuntimeHealth,
    RuntimeIdentity,
    RuntimeState,
)

if TYPE_CHECKING:
    from keyhole_sdk.transport.http import HttpTransport

# Required public contract fields by endpoint
_REQUIRED_IDENTITY_FIELDS = {
    "runtime_id",
    "runtime_name",
    "runtime_version",
    "environment",
    "capabilities",
}
_REQUIRED_STATE_FIELDS = {"updated_at"}


class SystemSurface:
    """System-level operations: health, compatibility."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def health(self) -> RuntimeHealth:
        """Return typed runtime health (GET /healthz)."""
        from pydantic import ValidationError

        data = self._transport.request("GET", "/healthz")
        try:
            return RuntimeHealth.model_validate(data)
        except ValidationError as exc:
            raise SchemaError(
                f"Health response does not match RuntimeHealth model: {exc}",
                raw_data=data,
            ) from exc

    def check_compatibility(self) -> CompatibilityResult:
        """Check SDK / runtime compatibility deterministically."""
        now = datetime.now(timezone.utc).isoformat()
        failures: list[str] = []
        warnings: list[str] = []
        runtime_name = "unknown"
        runtime_version = "unknown"

        # 1 — identity surface
        try:
            identity_data = self._transport.request("GET", "/identity")
        except TransportError as exc:
            return CompatibilityResult(
                sdk_version=__version__,
                runtime_name="unreachable",
                runtime_version="unreachable",
                compatibility_status=CompatibilityStatus.INCOMPATIBLE,
                failures=[f"transport: {exc}"],
                checked_at=now,
            )
        except (RuntimeUnavailableError, PublicEndpointError) as exc:
            return CompatibilityResult(
                sdk_version=__version__,
                runtime_name="error",
                runtime_version="error",
                compatibility_status=CompatibilityStatus.INCOMPATIBLE,
                failures=[f"identity endpoint: {exc}"],
                checked_at=now,
            )

        runtime_name = identity_data.get("runtime_name", "unknown")
        runtime_version = identity_data.get("runtime_version", "unknown")

        missing_id = _REQUIRED_IDENTITY_FIELDS - set(identity_data.keys())
        if missing_id:
            failures.append(f"identity missing required fields: {sorted(missing_id)}")

        # 2 — parse identity into typed model
        from pydantic import ValidationError

        try:
            RuntimeIdentity.model_validate(identity_data)
        except ValidationError as exc:
            failures.append(f"identity schema mismatch: {exc}")

        # 3 — health surface
        try:
            self._transport.request("GET", "/healthz")
        except (TransportError, RuntimeUnavailableError, PublicEndpointError) as exc:
            failures.append(f"healthz: {exc}")

        # 4 — state surface
        try:
            state_data = self._transport.request("GET", "/state")
            missing_st = _REQUIRED_STATE_FIELDS - set(state_data.keys())
            if missing_st:
                warnings.append(f"state missing optional fields: {sorted(missing_st)}")
            RuntimeState.model_validate(state_data)
        except (TransportError, RuntimeUnavailableError, PublicEndpointError) as exc:
            warnings.append(f"state endpoint: {exc}")
        except ValidationError as exc:
            warnings.append(f"state schema: {exc}")

        # 5 — determine outcome
        if failures:
            status = CompatibilityStatus.INCOMPATIBLE
        elif warnings:
            status = CompatibilityStatus.COMPATIBLE_WITH_WARNINGS
        else:
            status = CompatibilityStatus.COMPATIBLE

        return CompatibilityResult(
            sdk_version=__version__,
            runtime_name=runtime_name,
            runtime_version=runtime_version,
            compatibility_status=status,
            failures=failures,
            warnings=warnings,
            checked_at=now,
        )
