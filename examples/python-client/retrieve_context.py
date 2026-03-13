"""Keyhole SDK — Governed Context Retrieval example.

CE-V5-S42-05: Governed Context Retrieval Bootstrap.
Canonical example: retrieve governed context before work.

This example demonstrates the correct external participant sequence:

  1. Discover the boundary (capabilities)
  2. Bootstrap identity (authenticate with OIDC/PKCE token)
  3. Retrieve governed context through MCP
  4. Only then begin implementation, dispatch, or assumption-making

Usage:
    export KEYHOLE_MCP_URL="https://boundary.example.com"
    export KEYHOLE_MCP_TOKEN="<bearer-token>"
    python retrieve_context.py
"""

from __future__ import annotations

import os
import sys

from keyhole_sdk import (
    CapabilitiesClient,
    ContextClient,
    TransportError,
)
from keyhole_sdk.exceptions import AuthenticationError, SchemaError


def main() -> None:
    base_url = os.environ.get("KEYHOLE_MCP_URL", "")
    token = os.environ.get("KEYHOLE_MCP_TOKEN", "")

    if not base_url:
        print("Set KEYHOLE_MCP_URL to the MCP boundary URL.", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("Set KEYHOLE_MCP_TOKEN to a valid bearer token.", file=sys.stderr)
        sys.exit(1)

    # ── Step 1: Discover the boundary ────────────────────
    print("Step 1 — Discovering boundary...")
    with CapabilitiesClient(base_url) as discovery:
        caps = discovery.fetch()
        print(f"  Contract: {caps.get_contract_version()}")
        print(f"  Transport: {caps.get_transport()}")
        print(f"  Auth flow: {caps.get_auth_flow()}")
        print(f"  Context surfaces: {caps.get_implemented_context_surfaces()}")

    # ── Step 2: Identity already bootstrapped via token ───
    print("Step 2 — Identity bootstrapped (token provided).")

    # ── Step 3: Retrieve governed context ────────────────
    print("Step 3 — Retrieving governed context...")
    with ContextClient(base_url=base_url, token=token) as ctx:
        snapshot = ctx.compile_context()
        print(f"  Platform: {snapshot.get_platform_name()}")
        print(f"  Governance: {snapshot.get_governance_model()}")
        print(f"  MCP contract: {snapshot.get_mcp_contract()}")
        print(f"  Digest: {snapshot.get_digest()}")
        print(f"  Surfaces: {snapshot.get_implemented_surfaces()}")

    # ── Step 4: Now proceed with governed truth ──────────
    print("Step 4 — Context retrieved. Ready to proceed with governed truth.")
    print()
    print("The participant now has boundary-verified context.")
    print("Implementation, dispatch, or design may begin.")


if __name__ == "__main__":
    try:
        main()
    except TransportError as exc:
        print(f"Transport error: {exc}", file=sys.stderr)
        sys.exit(1)
    except AuthenticationError as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        sys.exit(1)
    except SchemaError as exc:
        print(f"Schema error: {exc}", file=sys.stderr)
        sys.exit(1)
