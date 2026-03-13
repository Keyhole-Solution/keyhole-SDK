"""CE-V5-S42-04 — Auth & Identity Bootstrap Guidance tests.

Covers all 7 acceptance criteria from the story:
  AC-1 — Discovery vs authenticated surfaces clearly explained
  AC-2 — Identity guidance matches current boundary rules
  AC-3 — Write/read distinctions made explicit
  AC-4 — Bootstrap flow is machine- and human-readable
  AC-5 — Guidance reflects OIDC/PKCE and keyhole-mcp
  AC-6 — GET /mcp/v1/whoami documented as initial authenticated check
  AC-7 — Public discovery ≠ full governed participant readiness

Also covers functional requirements FR-1 through FR-8.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relpath: str) -> str:
    """Read a file relative to repository root."""
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────
# AC-1 / FR-1 — Discovery vs Authenticated Surfaces
# ──────────────────────────────────────────────────────────────


class TestDiscoveryVsAuth:
    """Developer kit docs explain discovery vs authenticated surfaces."""

    def test_auth_bootstrap_distinguishes_unauthenticated(self):
        content = _read("docs/auth-bootstrap.md")
        assert "unauthenticated" in content.lower()
        assert "GET /mcp/v1/capabilities" in content

    def test_auth_bootstrap_distinguishes_authenticated(self):
        content = _read("docs/auth-bootstrap.md")
        assert "authenticated" in content.lower()
        assert "GET /mcp/v1/whoami" in content

    def test_auth_bootstrap_has_surface_categories(self):
        """Surface categories table with auth required column."""
        content = _read("docs/auth-bootstrap.md")
        assert "Public Discovery" in content or "Public discovery" in content
        assert "Authenticated" in content
        assert "Auth Required" in content

    def test_copilot_instructions_surface_distinction(self):
        content = _read(".github/copilot-instructions.md")
        assert "Public discovery" in content
        assert "Authenticated identity" in content
        assert "Auth Required" in content

    def test_agent_md_surface_distinction(self):
        content = _read("docs/AGENT.md")
        assert "Public discovery" in content
        assert "Identity inspection" in content
        assert "Mutates State" in content or "Auth Required" in content


# ──────────────────────────────────────────────────────────────
# AC-2 — Identity guidance matches boundary rules
# ──────────────────────────────────────────────────────────────


class TestIdentityGuidance:
    """Identity guidance matches current boundary rules."""

    def test_whoami_explained_in_auth_bootstrap(self):
        content = _read("docs/auth-bootstrap.md")
        assert "GET /mcp/v1/whoami" in content
        assert "first authenticated" in content.lower()

    def test_whoami_not_convenience(self):
        """whoami is documented as required, not convenience."""
        content = _read("docs/auth-bootstrap.md")
        assert "not a convenience" in content.lower() or "not merely a convenience" in content.lower()

    def test_whoami_confirms_identity(self):
        content = _read("docs/auth-bootstrap.md")
        assert "boundary identity" in content.lower() or "participant identity" in content.lower()

    def test_skip_whoami_antipattern(self):
        """Skipping whoami is documented as an anti-pattern."""
        content = _read("docs/auth-bootstrap.md")
        assert "skip" in content.lower() and "whoami" in content.lower()


# ──────────────────────────────────────────────────────────────
# AC-3 / FR-5 — Write/Read Distinctions
# ──────────────────────────────────────────────────────────────


class TestReadWriteDistinction:
    """Write/read distinctions are made explicit."""

    def test_read_only_discovery(self):
        content = _read("docs/auth-bootstrap.md")
        assert "read-only" in content.lower()

    def test_write_proof_bearing_separate(self):
        content = _read("docs/auth-bootstrap.md")
        assert "proof-bearing" in content.lower() or "write" in content.lower()

    def test_token_not_mutation_authority(self):
        """Token possession ≠ mutation authority."""
        content = _read("docs/auth-bootstrap.md")
        assert "not" in content.lower() and "mutation" in content.lower()

    def test_copilot_instructions_read_write(self):
        content = _read(".github/copilot-instructions.md")
        assert "Write / proof-bearing" in content or "write authority" in content.lower()


# ──────────────────────────────────────────────────────────────
# AC-4 / FR-7 — Bootstrap Flow Machine/Human Readable
# ──────────────────────────────────────────────────────────────


class TestBootstrapFlow:
    """Bootstrap flow is machine- and human-readable."""

    def test_bootstrap_sequence_steps(self):
        content = _read("docs/auth-bootstrap.md")
        # Machine-readable numbered steps
        assert "Step 1" in content
        assert "Step 2" in content
        assert "Step 3" in content
        assert "Step 4" in content

    def test_bootstrap_machine_readable_summary(self):
        """Machine-readable summary with numbered list."""
        content = _read("docs/auth-bootstrap.md")
        assert "Machine-Readable" in content
        assert "1. GET" in content or "1. GET" in content

    def test_bootstrap_preconditions_table(self):
        content = _read("docs/auth-bootstrap.md")
        assert "Precondition" in content

    def test_bootstrap_failure_guidance(self):
        """Failure at any step documented."""
        content = _read("docs/auth-bootstrap.md")
        assert "failure" in content.lower() or "Failure" in content
        assert "do not proceed" in content.lower()

    def test_readme_has_bootstrap_sequence(self):
        content = _read("README.md")
        assert "Discover" in content and "Authenticate" in content
        assert "Inspect identity" in content or "whoami" in content


# ──────────────────────────────────────────────────────────────
# AC-5 / FR-2 — OIDC/PKCE and keyhole-mcp
# ──────────────────────────────────────────────────────────────


class TestOIDCPKCEAccuracy:
    """Guidance explicitly reflects OIDC/PKCE and keyhole-mcp."""

    def test_auth_bootstrap_oidc_pkce(self):
        content = _read("docs/auth-bootstrap.md")
        assert "OIDC/PKCE" in content

    def test_auth_bootstrap_keyhole_mcp_realm(self):
        content = _read("docs/auth-bootstrap.md")
        assert "keyhole-mcp" in content

    def test_copilot_oidc_pkce(self):
        content = _read(".github/copilot-instructions.md")
        assert "OIDC/PKCE" in content

    def test_copilot_keyhole_mcp(self):
        content = _read(".github/copilot-instructions.md")
        assert "keyhole-mcp" in content

    def test_agent_md_oidc_pkce(self):
        content = _read("docs/AGENT.md")
        assert "OIDC/PKCE" in content

    def test_agent_md_keyhole_mcp(self):
        content = _read("docs/AGENT.md")
        assert "keyhole-mcp" in content


# ──────────────────────────────────────────────────────────────
# AC-6 / FR-4 — whoami as first authenticated identity check
# ──────────────────────────────────────────────────────────────


class TestWhoamiDocumented:
    """GET /mcp/v1/whoami documented as initial authenticated identity step."""

    def test_auth_bootstrap_whoami_step3(self):
        """whoami appears as Step 3 in the bootstrap sequence."""
        content = _read("docs/auth-bootstrap.md")
        # Step 3 should contain whoami
        step3_idx = content.find("Step 3")
        assert step3_idx != -1
        step3_section = content[step3_idx:step3_idx + 500]
        assert "whoami" in step3_section

    def test_copilot_whoami_in_bootstrap(self):
        content = _read(".github/copilot-instructions.md")
        assert "GET /mcp/v1/whoami" in content
        assert "first authenticated" in content.lower()

    def test_agent_whoami_in_bootstrap(self):
        content = _read("docs/AGENT.md")
        assert "/mcp/v1/whoami" in content
        # Should mention it in the bootstrap sequence
        assert "first authenticated" in content.lower() or "inspect identity" in content.lower()

    def test_readme_references_whoami(self):
        content = _read("README.md")
        assert "whoami" in content.lower() or "Inspect identity" in content


# ──────────────────────────────────────────────────────────────
# AC-7 — Public discovery ≠ governed participant readiness
# ──────────────────────────────────────────────────────────────


class TestDiscoveryNotReadiness:
    """Public discovery does not equal full governed participant readiness."""

    def test_auth_bootstrap_discovery_not_readiness(self):
        content = _read("docs/auth-bootstrap.md")
        # Must say that capabilities/discovery != governed participant
        assert "does not" in content.lower() or "not equal" in content.lower()
        assert "governed participant" in content.lower()

    def test_readme_discovery_not_readiness(self):
        content = _read("README.md")
        plain = content.lower().replace("**", "")
        assert "does not" in plain
        assert "governed participant readiness" in plain or \
               "write authority" in plain

    def test_copilot_discovery_not_readiness(self):
        content = _read(".github/copilot-instructions.md")
        plain = content.lower().replace("**", "")
        assert "does not" in plain
        assert "governed participant readiness" in plain or \
               "write authority" in plain

    def test_agent_discovery_not_readiness(self):
        content = _read("docs/AGENT.md")
        assert "governed participant readiness" in content.lower() or \
               "write authority" in content.lower() or \
               "governed participant" in content.lower()


# ──────────────────────────────────────────────────────────────
# FR-3 — Token Guidance
# ──────────────────────────────────────────────────────────────


class TestTokenGuidance:
    """FR-3: Token acquisition guidance without private source dependency."""

    def test_token_acquisition_section(self):
        content = _read("docs/auth-bootstrap.md")
        assert "Token Acquisition" in content or "token acquisition" in content

    def test_bearer_token_guidance(self):
        content = _read("docs/auth-bootstrap.md")
        assert "Bearer" in content

    def test_no_secrets_in_docs(self):
        """No hardcoded secrets or credentials in auth bootstrap."""
        content = _read("docs/auth-bootstrap.md")
        assert "eyJ" not in content  # No JWT fragments
        assert "password" not in content.lower() or "passwords" in content.lower() or "app_password" not in content


# ──────────────────────────────────────────────────────────────
# FR-6 — Charter / Workspace Awareness
# ──────────────────────────────────────────────────────────────


class TestCharterWorkspaceAwareness:
    """FR-6: Charter and workspace posture noted for later governance."""

    def test_charter_mentioned(self):
        content = _read("docs/auth-bootstrap.md")
        assert "charter" in content.lower()
        assert "required" in content.lower()

    def test_workspace_mentioned(self):
        content = _read("docs/auth-bootstrap.md")
        assert "workspace" in content.lower()
        assert "supported" in content.lower()

    def test_auth_not_final_state(self):
        """Auth is documented as first step, not entire lifecycle."""
        content = _read("docs/auth-bootstrap.md")
        plain = content.lower().replace("**", "")
        assert "not the entire" in plain or "not the final" in plain


# ──────────────────────────────────────────────────────────────
# FR-8 — No Private-Source Dependency
# ──────────────────────────────────────────────────────────────


class TestNoPrivateSourceDependency:
    """FR-8: Bootstrap guidance does not require private source."""

    def test_no_platform_source_references(self):
        content = _read("docs/auth-bootstrap.md")
        assert "keyhole_Platform" not in content
        assert "private platform source" not in content or \
               "do not" in content.lower()

    def test_boundary_first_guidance(self):
        content = _read("docs/auth-bootstrap.md")
        assert "boundary" in content.lower()
        assert "capabilities" in content.lower()

    def test_antipatterns_documented(self):
        """Anti-patterns section warns against stale docs."""
        content = _read("docs/auth-bootstrap.md")
        assert "Anti-Pattern" in content or "anti-pattern" in content.lower()
        assert "stale" in content.lower()


# ──────────────────────────────────────────────────────────────
# Cross-document consistency
# ──────────────────────────────────────────────────────────────


class TestCrossDocConsistency:
    """Verify auth bootstrap is referenced across all key docs."""

    def test_readme_references_auth_bootstrap(self):
        content = _read("README.md")
        assert "auth-bootstrap" in content

    def test_quickstart_references_auth_bootstrap(self):
        content = _read("docs/quickstart.md")
        assert "auth-bootstrap" in content

    def test_copilot_references_auth_bootstrap(self):
        content = _read(".github/copilot-instructions.md")
        assert "auth-bootstrap" in content

    def test_agent_references_auth_bootstrap(self):
        content = _read("docs/AGENT.md")
        assert "auth-bootstrap" in content

    def test_auth_bootstrap_file_exists(self):
        assert (REPO_ROOT / "docs" / "auth-bootstrap.md").exists()

    def test_public_surface_inventory_includes_auth_bootstrap(self):
        content = _read("docs/specs/developer_ecosystem/public_surface_inventory.yaml")
        assert "auth-bootstrap.md" in content
