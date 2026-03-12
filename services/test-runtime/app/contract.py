"""Public Runtime Bridge Surface Contract.

Defines the contract version, supported modes, runtime interfaces, and
identity/state/realize behavior that external builders should rely on.

This contract is subordinate to the external bridge law proven in S40-07.
Public ergonomics (Docker, Compose, Traefik examples) do NOT replace
constitutional bridge proof.
"""
from __future__ import annotations

CONTRACT_VERSION = "0.1.0"
SURFACE_VERSION = "s41-06"

# The public runtime bridge surface contract
RUNTIME_BRIDGE_CONTRACT = {
    "contract_version": CONTRACT_VERSION,
    "surface_version": SURFACE_VERSION,
    "supported_modes": ["local-only", "governed"],
    "startup_methods": ["docker-run", "docker-compose", "uvicorn-direct"],
    "runtime_interfaces": {
        "health": {"method": "GET", "path": "/healthz", "auth_required": False},
        "identity": {"method": "GET", "path": "/identity", "auth_required": False},
        "state": {"method": "GET", "path": "/state", "auth_required": False},
        "realize": {"method": "POST", "path": "/realize", "auth_required": False},
        "mode": {"method": "GET", "path": "/mode", "auth_required": False},
    },
    "identity_contract": {
        "runtime_id": "keyhole-test-runtime",
        "required_fields": [
            "runtime_id",
            "runtime_name",
            "runtime_version",
            "environment",
            "capabilities",
            "governance_mode",
        ],
        "capabilities": ["realize", "state", "health"],
    },
    "state_contract": {
        "required_fields": ["current_digest", "realized_digests", "updated_at"],
        "behavior": (
            "State reflects local runtime truth. In local-only mode, state "
            "mutations are not auditable upstream. In governed mode, state "
            "mutations occur only after governance approval."
        ),
    },
    "realize_contract": {
        "required_fields": ["candidate_digest"],
        "optional_fields": [
            "payload",
            "promotion_uuid",
            "artifact_refs",
            "expected_capabilities",
            "lane",
            "purpose",
        ],
        "receipt_fields": ["digest", "status", "message", "realized_at"],
        "behavior": (
            "In local-only mode, realize executes immediately. "
            "In governed mode, realize is gated through MCP governance. "
            "Idempotent: re-submitting a realized digest returns ALREADY_REALIZED."
        ),
    },
    "mode_contract": {
        "modes": {
            "local-only": {
                "mcp_configured": False,
                "auditable_upstream": False,
                "governance_gating": False,
                "evidence_implication": "None — local results only",
            },
            "governed": {
                "mcp_configured": True,
                "auditable_upstream": True,
                "governance_gating": True,
                "evidence_implication": (
                    "Upstream evidence may exist when properly configured. "
                    "Does NOT automatically imply canonical promotion."
                ),
            },
        },
    },
    "bridge_law_reference": "CE-V5-S40-07",
    "public_safety_note": (
        "This contract describes the public runtime bridge surface. "
        "It does not expose internal production routing, controller topology, "
        "or enforcement chain details. Remote target examples are bounded "
        "and do not disclose internal platform architecture."
    ),
}
