"""Safe dispatch example — discover, validate, preflight, then dispatch.

CE-V5-S42-06: Run-Type Safety & Schema Discovery Helpers.

Demonstrates the correct participant posture for run dispatch:

  Step 1 — Discover capabilities (learn what the boundary publishes)
  Step 2 — Validate the intended run type (check before dispatch)
  Step 3 — Preflight the dispatch (confirm request shape)
  Step 4 — Dispatch only after safety check

Requires:
  KEYHOLE_MCP_URL   — MCP boundary base URL
  KEYHOLE_MCP_TOKEN — Bearer token (from OIDC/PKCE)

Usage:
  export KEYHOLE_MCP_URL=https://boundary.example.com
  export KEYHOLE_MCP_TOKEN=<your-token>
  python safe_dispatch.py
"""

import os
import sys

from keyhole_sdk import (
    CapabilitiesClient,
    ContextClient,
    DispatchPreflight,
    RunTypeValidator,
    SchemaHelper,
)
from keyhole_sdk.dispatch import PreflightStatus


def main() -> None:
    url = os.environ.get("KEYHOLE_MCP_URL", "")
    token = os.environ.get("KEYHOLE_MCP_TOKEN", "")

    if not url or not token:
        print("Set KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN first.")
        sys.exit(1)

    # ── Step 1: Discover capabilities ──────────────────────
    print("Step 1: Discovering capabilities...")
    with CapabilitiesClient(base_url=url) as caps_client:
        caps = caps_client.fetch()

    print(f"  Contract: {caps.get_contract_version()}")
    print(f"  Run-type rule: {caps.get_run_type_rule()}")
    print(f"  Surfaces: {caps.get_implemented_context_surfaces()}")

    # ── Step 2: Build safety helpers from capabilities ─────
    print("\nStep 2: Building dispatch safety layer...")
    preflight = DispatchPreflight.from_capabilities(caps)
    validator = RunTypeValidator.from_capabilities(caps)
    schema = SchemaHelper.from_capabilities(caps)

    # ── Step 3: Validate and preflight ─────────────────────
    # Example: correct run type
    run_type = "context.compile"
    print(f"\nStep 3a: Validating '{run_type}'...")
    check = validator.check(run_type)
    print(f"  Status: {check.status.value} — {check.reason}")

    result = preflight.check(run_type)
    print(f"  Preflight: {result.status.value} — {result.reason}")

    # Example: incorrect run type
    bad_name = "gaps.states"
    print(f"\nStep 3b: Validating '{bad_name}'...")
    check = validator.check(bad_name)
    print(f"  Status: {check.status.value} — {check.reason}")
    if check.suggestions:
        print(f"  Suggestions: {check.suggestions}")

    result = preflight.check(bad_name)
    print(f"  Preflight: {result.status.value} — {result.reason}")
    print(f"  Next step: {result.suggested_next_step}")

    # Example: missing required param
    print(f"\nStep 3c: Preflight 'lineage.get.v0_1' without target...")
    result = preflight.check("lineage.get.v0_1", params={})
    print(f"  Preflight: {result.status.value}")
    for w in result.warnings:
        print(f"  Warning: {w}")

    # Example: correct with required param
    print(f"\nStep 3d: Preflight 'lineage.get.v0_1' with target...")
    result = preflight.check(
        "lineage.get.v0_1",
        params={"target": "my-artifact"},
    )
    print(f"  Preflight: {result.status.value} — {result.reason}")

    # ── Step 4: Dispatch only after passing preflight ──────
    print("\nStep 4: Dispatching after successful preflight...")
    result = preflight.check("context.compile")
    if result.should_proceed:
        with ContextClient(base_url=url, token=token) as ctx:
            snapshot = ctx.compile_context()
        print(f"  Platform: {snapshot.get_platform_name()}")
        print(f"  Digest: {snapshot.get_digest()}")
    else:
        print(f"  Dispatch blocked: {result.reason}")

    # ── Error recovery example ─────────────────────────────
    print("\nError recovery guidance for 'gap.status':")
    guidance = preflight.get_recovery_guidance("gap.status")
    print(f"  Error class: {guidance.error_class}")
    print(f"  Message: {guidance.message}")
    for action in guidance.actions:
        print(f"  → {action.action}: {action.detail}")


if __name__ == "__main__":
    main()
