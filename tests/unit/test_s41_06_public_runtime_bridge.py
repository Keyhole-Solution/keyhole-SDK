"""CE-V5-S41-06 — Public Runtime Bridge Surface Tests

Validates all invariants sealed by the Public Runtime Bridge Surface story:

  INV-PUBLIC-RUNTIME-REPRODUCIBLE (structural)
  INV-PUBLIC-RUNTIME-MODE-TRUTHFUL (constitutional)
  INV-PUBLIC-RUNTIME-CONTRACT-ALIGNED (structural)
  INV-PUBLIC-RUNTIME-BRIDGE-LAW-SUBORDINATE (constitutional)
  INV-PUBLIC-RUNTIME-LOCAL-ONLY-NON-AUDITABLE (structural)
  INV-PUBLIC-RUNTIME-GOVERNED-PATH-EXPLAINED (structural)
  INV-PUBLIC-RUNTIME-REMOTE-TARGET-TRUTHFUL (structural)
"""
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]  # keyhole-developer-kit-main
TEST_RUNTIME_DIR = REPO_ROOT / "services" / "test-runtime"
APP_DIR = TEST_RUNTIME_DIR / "app"
EXAMPLES_DIR = TEST_RUNTIME_DIR / "examples"

# Platform repo root (one level above developer kit)
PLATFORM_ROOT = REPO_ROOT.parent
DEPLOY_DIR = PLATFORM_ROOT / "deploy"
DOCS_DIR = PLATFORM_ROOT / "docs"


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-REPRODUCIBLE
# ---------------------------------------------------------------------------
class TestRuntimeReproducible:
    """The public runtime must be launchable reproducibly through canonical
    Dockerized and Compose-supported flows."""

    def test_dockerfile_exists(self) -> None:
        assert (TEST_RUNTIME_DIR / "Dockerfile").is_file()

    def test_dockerfile_has_required_elements(self) -> None:
        content = (TEST_RUNTIME_DIR / "Dockerfile").read_text()
        assert "FROM python:" in content
        assert "EXPOSE 8080" in content
        assert "HEALTHCHECK" in content
        assert "CMD" in content
        assert "uvicorn" in content.lower() or "app.main:app" in content

    def test_requirements_exists(self) -> None:
        req = TEST_RUNTIME_DIR / "requirements.txt"
        assert req.is_file()
        content = req.read_text()
        assert "fastapi" in content
        assert "uvicorn" in content

    def test_app_modules_exist(self) -> None:
        for module in ("main.py", "routes.py", "models.py", "state.py",
                       "bridge.py", "mode.py", "contract.py"):
            assert (APP_DIR / module).is_file(), f"Missing {module}"

    def test_compose_public_runtime_exists(self) -> None:
        assert (DEPLOY_DIR / "compose.public-runtime.yml").is_file()

    def test_compose_valid_yaml(self) -> None:
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        data = yaml.safe_load(path.read_text())
        assert "services" in data
        # At least one service defined
        assert len(data["services"]) >= 1

    def test_compose_has_healthcheck(self) -> None:
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        data = yaml.safe_load(path.read_text())
        for svc in data["services"].values():
            assert "healthcheck" in svc, "Compose service must define healthcheck"

    def test_compose_has_mcp_env_vars(self) -> None:
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        content = path.read_text()
        assert "KEYHOLE_MCP_URL" in content
        assert "KEYHOLE_MCP_TOKEN" in content


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-MODE-TRUTHFUL
# ---------------------------------------------------------------------------
class TestRuntimeModeTruthful:
    """The public runtime must explicitly signal whether it is operating in
    local-only or governed mode."""

    def test_mode_module_exists(self) -> None:
        assert (APP_DIR / "mode.py").is_file()

    def test_mode_module_defines_resolve_mode(self) -> None:
        tree = ast.parse((APP_DIR / "mode.py").read_text())
        func_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert "resolve_mode" in func_names

    def test_mode_module_defines_mode_status(self) -> None:
        tree = ast.parse((APP_DIR / "mode.py").read_text())
        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        assert "ModeStatus" in class_names

    def test_mode_values_are_explicit(self) -> None:
        content = (APP_DIR / "mode.py").read_text()
        assert '"local-only"' in content
        assert '"governed"' in content
        assert '"misconfigured"' in content

    def test_identity_exposes_governance_mode(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        assert "governance_mode" in content

    def test_mode_endpoint_exists_in_routes(self) -> None:
        content = (APP_DIR / "routes.py").read_text()
        assert '"/mode"' in content

    def test_startup_log_signals_mode(self) -> None:
        content = (APP_DIR / "main.py").read_text()
        assert "GOVERNED" in content or "governed" in content.lower()
        assert "LOCAL-ONLY" in content or "local-only" in content.lower()


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-CONTRACT-ALIGNED
# ---------------------------------------------------------------------------
class TestRuntimeContractAligned:
    """Runtime identity/state/realize behavior must remain aligned with
    the public CLI, SDK, and runtime contract surfaces."""

    def test_contract_module_exists(self) -> None:
        assert (APP_DIR / "contract.py").is_file()

    def test_contract_defines_version(self) -> None:
        content = (APP_DIR / "contract.py").read_text()
        assert "CONTRACT_VERSION" in content
        assert "SURFACE_VERSION" in content

    def test_contract_defines_bridge_contract(self) -> None:
        content = (APP_DIR / "contract.py").read_text()
        assert "RUNTIME_BRIDGE_CONTRACT" in content

    def test_contract_has_required_sections(self) -> None:
        # Import the contract module to validate structure
        sys.path.insert(0, str(APP_DIR.parent))
        try:
            spec = {}
            exec((APP_DIR / "contract.py").read_text(), spec)
            c = spec["RUNTIME_BRIDGE_CONTRACT"]
            assert "contract_version" in c
            assert "supported_modes" in c
            assert "runtime_interfaces" in c
            assert "identity_contract" in c
            assert "state_contract" in c
            assert "realize_contract" in c
            assert "mode_contract" in c
            assert "bridge_law_reference" in c
        finally:
            sys.path.pop(0)

    def test_identity_model_has_required_fields(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        for field in ("runtime_id", "runtime_name", "runtime_version",
                       "environment", "capabilities", "governance_mode"):
            assert field in content, f"IdentityResponse missing {field}"

    def test_state_model_has_required_fields(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        for field in ("current_digest", "realized_digests", "updated_at"):
            assert field in content, f"StateResponse missing {field}"

    def test_realize_receipt_has_required_fields(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        for field in ("digest", "status", "message", "realized_at"):
            assert field in content, f"RealizationReceipt missing {field}"

    def test_contract_endpoint_in_routes(self) -> None:
        content = (APP_DIR / "routes.py").read_text()
        assert '"/contract"' in content


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-BRIDGE-LAW-SUBORDINATE
# ---------------------------------------------------------------------------
class TestRuntimeBridgeLawSubordinate:
    """The public runtime must remain subordinate to the external bridge law
    proven in S40-07."""

    def test_contract_references_s40_07(self) -> None:
        content = (APP_DIR / "contract.py").read_text()
        assert "S40-07" in content or "CE-V5-S40-07" in content

    def test_contract_has_public_safety_note(self) -> None:
        content = (APP_DIR / "contract.py").read_text()
        assert "public_safety_note" in content

    def test_spec_doc_references_bridge_law(self) -> None:
        spec = DOCS_DIR / "specs" / "developer_ecosystem" / "public_runtime_bridge_surface.md"
        assert spec.is_file()
        content = spec.read_text()
        assert "S40-07" in content

    def test_spec_doc_states_subordination(self) -> None:
        spec = DOCS_DIR / "specs" / "developer_ecosystem" / "public_runtime_bridge_surface.md"
        content = spec.read_text()
        assert "subordinate" in content.lower()

    def test_compose_does_not_overclaim_topology(self) -> None:
        """Compose file must not expose internal production topology."""
        content = (DEPLOY_DIR / "compose.public-runtime.yml").read_text()
        for forbidden in ("keyhole-system", "controller-manager",
                          "drift-stopper", "pointer-store"):
            assert forbidden not in content, \
                f"Compose file contains internal term: {forbidden}"

    def test_smoke_examples_reference_bridge_law(self) -> None:
        for name in ("local-smoke.json", "governed-smoke.json"):
            path = EXAMPLES_DIR / name
            assert path.is_file(), f"Missing {name}"
            data = json.loads(path.read_text())
            assert data.get("bridge_law_reference") == "CE-V5-S40-07"


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-LOCAL-ONLY-NON-AUDITABLE
# ---------------------------------------------------------------------------
class TestLocalOnlyNonAuditable:
    """Local-only runtime flows must explicitly declare that upstream Event
    Spine evidence and governed attestation are not implied."""

    def test_local_smoke_declares_non_auditable(self) -> None:
        path = EXAMPLES_DIR / "local-smoke.json"
        data = json.loads(path.read_text())
        posture = data.get("evidence_posture", "")
        assert "NOT auditable upstream" in posture or "not auditable" in posture.lower()

    def test_mode_module_disclaims_local_only(self) -> None:
        content = (APP_DIR / "mode.py").read_text()
        assert "NOT constitutional proof" in content or "not constitutional proof" in content.lower()

    def test_spec_doc_explains_local_evidence(self) -> None:
        spec = DOCS_DIR / "specs" / "developer_ecosystem" / "public_runtime_bridge_surface.md"
        content = spec.read_text()
        assert "Local-Only" in content
        assert "NOT constitutional proof" in content or "not constitutional proof" in content.lower()


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-GOVERNED-PATH-EXPLAINED
# ---------------------------------------------------------------------------
class TestGovernedPathExplained:
    """Governed runtime flows must explicitly describe MCP configuration,
    expected behavior, evidence, and isolation."""

    def test_governed_smoke_explains_mcp(self) -> None:
        path = EXAMPLES_DIR / "governed-smoke.json"
        data = json.loads(path.read_text())
        assert "mcp_configuration" in data
        cfg = data["mcp_configuration"]
        assert "KEYHOLE_MCP_URL" in cfg.get("required_env_vars", [])
        assert "KEYHOLE_MCP_TOKEN" in cfg.get("required_env_vars", [])

    def test_governed_smoke_explains_evidence(self) -> None:
        path = EXAMPLES_DIR / "governed-smoke.json"
        data = json.loads(path.read_text())
        posture = data.get("evidence_posture", "")
        assert "candidate" in posture.lower() or "isolation" in posture.lower()

    def test_spec_doc_explains_governed_mode(self) -> None:
        spec = DOCS_DIR / "specs" / "developer_ecosystem" / "public_runtime_bridge_surface.md"
        content = spec.read_text()
        assert "Governed Mode" in content
        assert "KEYHOLE_MCP_URL" in content
        assert "KEYHOLE_MCP_TOKEN" in content

    def test_academy_governed_doc_exists(self) -> None:
        doc = DOCS_DIR / "academy" / "runtime" / "governed-vs-local.md"
        assert doc.is_file()
        content = doc.read_text()
        assert "governed" in content.lower()
        assert "local" in content.lower()


# ---------------------------------------------------------------------------
# INV-PUBLIC-RUNTIME-REMOTE-TARGET-TRUTHFUL
# ---------------------------------------------------------------------------
class TestRemoteTargetTruthful:
    """Traefik-compatible remote target examples must be truthful, bounded,
    and public-safe."""

    def test_traefik_example_exists(self) -> None:
        path = DEPLOY_DIR / "traefik" / "traefik.public-runtime.example.yml"
        assert path.is_file()

    def test_traefik_example_valid_yaml(self) -> None:
        path = DEPLOY_DIR / "traefik" / "traefik.public-runtime.example.yml"
        data = yaml.safe_load(path.read_text())
        assert "services" in data

    def test_traefik_example_has_labels(self) -> None:
        path = DEPLOY_DIR / "traefik" / "traefik.public-runtime.example.yml"
        content = path.read_text()
        assert "traefik.enable=true" in content
        assert "traefik.http.routers" in content

    def test_traefik_example_does_not_expose_internals(self) -> None:
        path = DEPLOY_DIR / "traefik" / "traefik.public-runtime.example.yml"
        content = path.read_text()
        for forbidden in ("keyhole-system", "controller-manager",
                          "drift-stopper", "pointer-store", "nats.nats.svc"):
            assert forbidden not in content, \
                f"Traefik example contains internal term: {forbidden}"

    def test_traefik_example_uses_example_domain(self) -> None:
        path = DEPLOY_DIR / "traefik" / "traefik.public-runtime.example.yml"
        content = path.read_text()
        assert "example.yourdomain.com" in content or "yourdomain" in content

    def test_academy_remote_target_doc_exists(self) -> None:
        doc = DOCS_DIR / "academy" / "runtime" / "remote-target-example.md"
        assert doc.is_file()
        content = doc.read_text()
        assert "traefik" in content.lower() or "remote" in content.lower()


# ---------------------------------------------------------------------------
# Compose Launch Proof
# ---------------------------------------------------------------------------
class TestComposeLaunch:
    """Verify the Compose launch path is deterministic and documented."""

    def test_compose_has_port_mapping(self) -> None:
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        content = path.read_text()
        assert "8080" in content

    def test_compose_defaults_to_local_only(self) -> None:
        """MCP env vars should default to empty (= local-only)."""
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        content = path.read_text()
        # Default should be empty string for KEYHOLE_MCP_URL
        assert "KEYHOLE_MCP_URL:-}" in content or 'KEYHOLE_MCP_URL:-""' in content or "KEYHOLE_MCP_URL: " in content

    def test_compose_references_runtime_image(self) -> None:
        path = DEPLOY_DIR / "compose.public-runtime.yml"
        content = path.read_text()
        assert "KEYHOLE_RUNTIME_IMAGE" in content or "test-runtime" in content


# ---------------------------------------------------------------------------
# Contract Alignment (models match contract spec)
# ---------------------------------------------------------------------------
class TestContractModelsAlignment:
    """Verify that Pydantic models match the contract-defined fields."""

    def test_mode_response_matches_contract(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        for field in ("mode", "mcp_configured", "auditable_upstream", "evidence_disclaimer"):
            assert field in content, f"ModeResponse missing {field}"

    def test_contract_response_model_exists(self) -> None:
        content = (APP_DIR / "models.py").read_text()
        assert "ContractResponse" in content
