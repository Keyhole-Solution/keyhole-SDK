"""Read-only smoke path runner.

CE-V5-S42-07: Read-Only Smoke Path.

Orchestrates the first clean end-to-end read-only participant path:

  1. Discover — ``GET /mcp/v1/capabilities`` (unauthenticated)
  2. Inspect identity — ``GET /mcp/v1/whoami`` (authenticated)
  3. Retrieve context — ``context.compile`` via ContextClient
  4. Safe read-only run — ``gaps.list`` via ContextClient

Each phase produces a :class:`PhaseResult`.  The aggregate
:class:`SmokeResult` tells the participant whether the path
is fully open, partially open, or blocked.

This runner is strictly read-only.  It never mutates platform state.
It uses live MCP boundary surfaces — not mocks or local stubs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.context.client import ContextClient
from keyhole_sdk.dispatch.preflight import DispatchPreflight
from keyhole_sdk.exceptions import (
    AuthenticationError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.smoke.models import PhaseResult, SmokePhase, SmokeResult
from keyhole_sdk.config import DEFAULT_REALM


WHOAMI_PATH = "/mcp/v1/whoami"


class ReadOnlySmokeRunner:
    """Orchestrates a read-only smoke path against the MCP boundary.

    Usage::

        runner = ReadOnlySmokeRunner(
            base_url="https://boundary.example.com",
            token="<bearer-token>",
        )
        result = runner.run()
        print(result.summary())

    Or as a context manager::

        with ReadOnlySmokeRunner(base_url=url, token=token) as runner:
            result = runner.run()
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session = session or requests.Session()

    def run(self) -> SmokeResult:
        """Execute the full read-only smoke path.

        Runs each phase in order.  If a phase fails, subsequent
        phases that depend on it are skipped with a clear reason.
        """
        result = SmokeResult()

        # Phase 1: Discovery (unauthenticated)
        caps_result = self._phase_discovery()
        result.phases.append(caps_result)
        caps = caps_result.data.get("_capabilities")

        # Phase 2: Identity inspection (authenticated)
        identity_result = self._phase_identity()
        result.phases.append(identity_result)

        if not identity_result.success:
            # Cannot proceed to context/run without identity
            result.phases.append(PhaseResult(
                phase=SmokePhase.CONTEXT,
                error="Skipped — identity inspection failed.",
                suggestion="Fix authentication before retrying.",
            ))
            result.phases.append(PhaseResult(
                phase=SmokePhase.READONLY_RUN,
                error="Skipped — identity inspection failed.",
                suggestion="Fix authentication before retrying.",
            ))
            return result

        # Phase 3: Context retrieval (authenticated)
        context_result = self._phase_context()
        result.phases.append(context_result)

        # Phase 4: Safe read-only run (authenticated)
        run_result = self._phase_readonly_run(caps)
        result.phases.append(run_result)

        return result

    # ── Phase implementations ───────────────────────────────

    def _phase_discovery(self) -> PhaseResult:
        """Phase 1: Discover capabilities (unauthenticated)."""
        try:
            with CapabilitiesClient(
                self.base_url,
                timeout=self.timeout,
                session=self._session,
            ) as client:
                caps = client.fetch()

            data: Dict[str, Any] = {
                "contract_version": caps.get_contract_version(),
                "auth_flow": caps.get_auth_flow(),
                "transport": caps.get_transport(),
                "context_surfaces": caps.get_implemented_context_surfaces(),
                "_capabilities": caps,
            }
            return PhaseResult(
                phase=SmokePhase.DISCOVERY,
                success=True,
                data=data,
            )

        except TransportError as exc:
            return PhaseResult(
                phase=SmokePhase.DISCOVERY,
                error=str(exc),
                suggestion=(
                    "Check that the MCP boundary URL is correct and reachable. "
                    "Verify network connectivity."
                ),
            )
        except SchemaError as exc:
            return PhaseResult(
                phase=SmokePhase.DISCOVERY,
                error=str(exc),
                suggestion="The capabilities response is malformed. Check boundary version.",
            )

    def _phase_identity(self) -> PhaseResult:
        """Phase 2: Inspect identity via GET /mcp/v1/whoami."""
        url = f"{self.base_url}{WHOAMI_PATH}"
        try:
            response = self._session.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout, OSError) as exc:
            return PhaseResult(
                phase=SmokePhase.IDENTITY,
                error=f"Identity inspection failed: {exc}",
                suggestion="Check network connectivity to the MCP boundary.",
            )

        if response.status_code == 401:
            return PhaseResult(
                phase=SmokePhase.IDENTITY,
                error="Authentication failed (401). Token is invalid or expired.",
                suggestion=(
                    f"Acquire a fresh OIDC/PKCE token for realm '{DEFAULT_REALM}'. "
                    "See docs/auth-bootstrap.md."
                ),
            )

        if response.status_code == 403:
            return PhaseResult(
                phase=SmokePhase.IDENTITY,
                error="Insufficient authority (403).",
                suggestion="Check participant identity and charter posture.",
            )

        if response.status_code != 200:
            return PhaseResult(
                phase=SmokePhase.IDENTITY,
                error=f"Identity endpoint returned {response.status_code}.",
                suggestion="Unexpected status code. Check MCP boundary health.",
            )

        try:
            data = response.json()
        except ValueError:
            return PhaseResult(
                phase=SmokePhase.IDENTITY,
                error="Identity response is not valid JSON.",
                suggestion="Check boundary version compatibility.",
            )

        return PhaseResult(
            phase=SmokePhase.IDENTITY,
            success=True,
            data=data if isinstance(data, dict) else {"raw": data},
        )

    def _phase_context(self) -> PhaseResult:
        """Phase 3: Retrieve context via context.compile."""
        try:
            with ContextClient(
                self.base_url,
                token=self.token,
                timeout=self.timeout,
                session=self._session,
            ) as ctx:
                snapshot = ctx.compile_context()

            data: Dict[str, Any] = {
                "platform_name": snapshot.get_platform_name(),
                "governance_model": snapshot.get_governance_model(),
                "mcp_contract": snapshot.get_mcp_contract(),
                "implemented_surfaces": snapshot.get_implemented_surfaces(),
            }
            return PhaseResult(
                phase=SmokePhase.CONTEXT,
                success=True,
                data=data,
            )

        except AuthenticationError as exc:
            return PhaseResult(
                phase=SmokePhase.CONTEXT,
                error=str(exc),
                suggestion="Token may have expired between identity and context phases.",
            )
        except TransportError as exc:
            return PhaseResult(
                phase=SmokePhase.CONTEXT,
                error=str(exc),
                suggestion="Context retrieval failed. Check MCP boundary health.",
            )
        except SchemaError as exc:
            return PhaseResult(
                phase=SmokePhase.CONTEXT,
                error=str(exc),
                suggestion="Context response is malformed. Check boundary version.",
            )

    def _phase_readonly_run(
        self,
        caps: Any,
    ) -> PhaseResult:
        """Phase 4: Safe read-only run via gaps.list with preflight."""
        run_type = "gaps.list"

        # Preflight check if capabilities are available
        if caps is not None:
            try:
                preflight = DispatchPreflight.from_capabilities(caps)
                check = preflight.check(run_type)
                if not check.should_proceed:
                    return PhaseResult(
                        phase=SmokePhase.READONLY_RUN,
                        error=f"Preflight rejected {run_type}: {check.reason}",
                        suggestion=check.reason,
                    )
            except Exception as exc:
                # Preflight is advisory — proceed even if it fails
                pass

        try:
            with ContextClient(
                self.base_url,
                token=self.token,
                timeout=self.timeout,
                session=self._session,
            ) as ctx:
                response = ctx.list_gaps()

            data: Dict[str, Any] = {
                "run_type": response.run_type,
                "status": response.status,
                "has_data": bool(response.data),
            }
            return PhaseResult(
                phase=SmokePhase.READONLY_RUN,
                success=True,
                data=data,
            )

        except AuthenticationError as exc:
            return PhaseResult(
                phase=SmokePhase.READONLY_RUN,
                error=str(exc),
                suggestion="Token may not have authority for gaps.list.",
            )
        except TransportError as exc:
            return PhaseResult(
                phase=SmokePhase.READONLY_RUN,
                error=str(exc),
                suggestion="Read-only run failed. Check MCP boundary health.",
            )
        except SchemaError as exc:
            return PhaseResult(
                phase=SmokePhase.READONLY_RUN,
                error=str(exc),
                suggestion="Run response is malformed. Check boundary version.",
            )

    # ── Lifecycle ───────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "ReadOnlySmokeRunner":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
