"""SDK-CLIENT-18 — Memory Boundary Enforcement tests.

Verifies that the public SDK and CLI enforce the memory containment doctrine:
  - No direct canonical memory query/write surface is exposed publicly.
  - Illegal direct-memory attempts fail deterministically with repair guidance.
  - Lawful alternatives (context compile/inspect, governed runs) remain available.
  - Proof emission writes the correct artifacts.
  - The CLI 'memory' command rejects with the proper message.

Test classes:
  TestDirectMemoryAccessNotAllowedException  — exception shape and message
  TestMemoryBoundaryEnforcer                 — rejection function behavior
  TestNoPublicMemoryQueryOrWriteSurface      — SDK __all__ / namespace absence
  TestKeyholeCLINoDirectMemoryCommands       — CLI command absence / rejection
  TestPositiveLawfulAlternatives             — lawful surfaces remain available
  TestProofEmission                          — proof artifact shape and content
  TestMemoryBoundaryPublicSurface            — module exports and imports
  TestMessageQualityRule                     — repair guidance content quality
  TestMemoryBoundaryRejectionMessage         — canonical rejection string
  TestCLIMemoryRejectionCallback             — CLI memory_app callback behavior
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

import keyhole_sdk
from keyhole_sdk.exceptions import DirectMemoryAccessNotAllowed, KeyholeSDKError
from keyhole_sdk.memory_boundary import (
    MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES,
    MEMORY_BOUNDARY_REJECTION_MESSAGE,
    emit_memory_boundary_proof,
    get_memory_boundary_repair,
    reject_direct_memory_access,
)
from keyhole_sdk.memory_boundary.enforcer import (
    MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES as _ALTERNATIVES_FROM_ENFORCER,
)
from keyhole_sdk.memory_boundary.proof import emit_memory_boundary_proof as _proof_fn

from keyhole_cli.cli import app


# ─────────────────────────────────────────────────────────────────────────────
# TestDirectMemoryAccessNotAllowedException
# ─────────────────────────────────────────────────────────────────────────────


class TestDirectMemoryAccessNotAllowedException:
    def test_is_subclass_of_keyhole_sdk_error(self):
        exc = DirectMemoryAccessNotAllowed()
        assert isinstance(exc, KeyholeSDKError)

    def test_default_message_mentions_sdk(self):
        exc = DirectMemoryAccessNotAllowed()
        msg = str(exc)
        assert "public SDK" in msg

    def test_default_message_mentions_governed_context(self):
        exc = DirectMemoryAccessNotAllowed()
        msg = str(exc)
        assert "governed context" in msg.lower() or "governed" in msg.lower()

    def test_default_repair_guidance_is_populated(self):
        exc = DirectMemoryAccessNotAllowed()
        assert isinstance(exc.repair_guidance, list)
        assert len(exc.repair_guidance) >= 1

    def test_attempted_surface_stored(self):
        exc = DirectMemoryAccessNotAllowed(attempted_surface="client.memory.query")
        assert exc.attempted_surface == "client.memory.query"

    def test_attempted_surface_appears_in_message(self):
        exc = DirectMemoryAccessNotAllowed(attempted_surface="client.memory.query")
        assert "client.memory.query" in str(exc)

    def test_custom_repair_guidance_respected(self):
        guidance = ["use context compile instead"]
        exc = DirectMemoryAccessNotAllowed(repair_guidance=guidance)
        assert exc.repair_guidance == guidance

    def test_no_attempted_surface_message_still_coherent(self):
        exc = DirectMemoryAccessNotAllowed()
        msg = str(exc)
        assert len(msg) > 20  # meaningful message, not empty


# ─────────────────────────────────────────────────────────────────────────────
# TestMemoryBoundaryEnforcer
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryBoundaryEnforcer:
    def test_reject_raises_direct_memory_access_not_allowed(self):
        with pytest.raises(DirectMemoryAccessNotAllowed):
            reject_direct_memory_access("memory.query")

    def test_reject_includes_attempted_surface(self):
        with pytest.raises(DirectMemoryAccessNotAllowed) as exc_info:
            reject_direct_memory_access("client.memory.search")
        assert exc_info.value.attempted_surface == "client.memory.search"

    def test_reject_includes_repair_guidance_list(self):
        with pytest.raises(DirectMemoryAccessNotAllowed) as exc_info:
            reject_direct_memory_access("memory.write")
        assert isinstance(exc_info.value.repair_guidance, list)
        assert len(exc_info.value.repair_guidance) >= 1

    def test_repair_guidance_contains_context_compile(self):
        with pytest.raises(DirectMemoryAccessNotAllowed) as exc_info:
            reject_direct_memory_access("memory.get")
        guidance_text = " ".join(exc_info.value.repair_guidance)
        assert "context compile" in guidance_text

    def test_reject_with_extra_context_prepended(self):
        with pytest.raises(DirectMemoryAccessNotAllowed) as exc_info:
            reject_direct_memory_access(
                "memory.upsert",
                extra_context="See sdk-client-16 for context compile.",
            )
        assert "sdk-client-16" in exc_info.value.repair_guidance[0]

    def test_get_memory_boundary_repair_returns_list(self):
        result = get_memory_boundary_repair()
        assert isinstance(result, list)

    def test_get_memory_boundary_repair_is_a_copy(self):
        a = get_memory_boundary_repair()
        b = get_memory_boundary_repair()
        assert a == b
        a.append("extra")
        assert "extra" not in get_memory_boundary_repair()

    def test_lawful_alternatives_include_context_compile(self):
        assert any("context compile" in a for a in MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES)

    def test_lawful_alternatives_include_context_inspect(self):
        assert any("context inspect" in a for a in MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES)

    def test_lawful_alternatives_include_run_with_context(self):
        assert any("run" in a for a in MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES)


# ─────────────────────────────────────────────────────────────────────────────
# TestNoPublicMemoryQueryOrWriteSurface
# ─────────────────────────────────────────────────────────────────────────────


class TestNoPublicMemoryQueryOrWriteSurface:
    """Verify that no forbidden direct-memory symbols are in the public SDK surface."""

    FORBIDDEN_SYMBOLS = [
        "memory_query",
        "memory_write",
        "memory_search",
        "memory_get",
        "memory_upsert",
        "memory_delete",
        "MemoryQueryClient",
        "MemoryWriteClient",
        "DirectMemoryClient",
        "CanonicalMemoryClient",
    ]

    def test_sdk_all_has_no_memory_query_symbol(self):
        for sym in self.FORBIDDEN_SYMBOLS:
            assert sym not in keyhole_sdk.__all__, (
                f"Forbidden symbol {sym!r} must not appear in keyhole_sdk.__all__"
            )

    def test_keyhole_client_has_no_memory_attribute(self):
        from keyhole_sdk import KeyholeClient

        client = KeyholeClient.__new__(KeyholeClient)
        assert not hasattr(client, "memory"), (
            "KeyholeClient must not expose a 'memory' attribute."
        )

    def test_keyhole_sdk_module_has_no_direct_memory_namespace(self):
        # The module may have 'memory_boundary' (enforcement) but must not have
        # a raw 'memory' attribute that exposes canonical access.
        # If 'memory_boundary' is present that's intentional and correct.
        if hasattr(keyhole_sdk, "memory"):
            # There must be no callable query/write/search associated with it
            mem = getattr(keyhole_sdk, "memory")
            assert not callable(getattr(mem, "query", None)), (
                "keyhole_sdk.memory.query must not be callable"
            )
            assert not callable(getattr(mem, "write", None)), (
                "keyhole_sdk.memory.write must not be callable"
            )

    def test_no_memory_query_in_all(self):
        assert "memory_query" not in keyhole_sdk.__all__

    def test_no_memory_write_in_all(self):
        assert "memory_write" not in keyhole_sdk.__all__

    def test_sdk_all_includes_enforcement_surface(self):
        # The enforcement module IS allowed to export these symbols
        assert "DirectMemoryAccessNotAllowed" in keyhole_sdk.__all__
        assert "reject_direct_memory_access" in keyhole_sdk.__all__


# ─────────────────────────────────────────────────────────────────────────────
# TestKeyholeCLINoDirectMemoryCommands
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyholeCLINoDirectMemoryCommands:
    """Verify that the CLI does not expose direct canonical memory sub-commands."""

    def test_no_memory_query_subcommand_registered(self):
        from keyhole_cli.cli import memory_app

        registered_names = [cmd.name for cmd in memory_app.registered_commands]
        assert "query" not in registered_names

    def test_no_memory_write_subcommand_registered(self):
        from keyhole_cli.cli import memory_app

        registered_names = [cmd.name for cmd in memory_app.registered_commands]
        assert "write" not in registered_names

    def test_no_memory_get_subcommand_registered(self):
        from keyhole_cli.cli import memory_app

        registered_names = [cmd.name for cmd in memory_app.registered_commands]
        assert "get" not in registered_names

    def test_no_memory_delete_subcommand_registered(self):
        from keyhole_cli.cli import memory_app

        registered_names = [cmd.name for cmd in memory_app.registered_commands]
        assert "delete" not in registered_names

    def test_memory_app_is_registered_in_main_app(self):
        # Verify 'memory' typer sub-app IS registered (as a rejection surface)
        registered_names = [g.name for g in app.registered_groups]
        assert "memory" in registered_names


# ─────────────────────────────────────────────────────────────────────────────
# TestCLIMemoryRejectionCallback
# ─────────────────────────────────────────────────────────────────────────────


class TestCLIMemoryRejectionCallback:
    """Verify the CLI 'memory' command rejects with proper message."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_memory_command_exits_nonzero(self):
        result = self.runner.invoke(app, ["memory"])
        assert result.exit_code != 0

    def test_memory_command_outputs_reject_keyword(self):
        result = self.runner.invoke(app, ["memory"])
        output = result.output or ""
        assert "REJECT" in output or "not exposed" in output.lower()

    def test_memory_command_output_mentions_lawful_alternative(self):
        result = self.runner.invoke(app, ["memory"])
        output = result.output or ""
        assert (
            "context compile" in output
            or "context inspect" in output
            or "keyhole run" in output
        )

    def test_memory_command_output_mentions_governed(self):
        result = self.runner.invoke(app, ["memory"])
        output = result.output or ""
        assert "governed" in output.lower()


# ─────────────────────────────────────────────────────────────────────────────
# TestPositiveLawfulAlternatives
# ─────────────────────────────────────────────────────────────────────────────


class TestPositiveLawfulAlternatives:
    """Verify that lawful alternatives remain available in CLI and SDK."""

    def test_context_app_registered_in_cli(self):
        from keyhole_cli.cli import context_app

        assert context_app is not None

    def test_context_compile_command_exists(self):
        from keyhole_cli.cli import context_app

        cmd_names = [cmd.name for cmd in context_app.registered_commands]
        assert "compile" in cmd_names

    def test_context_inspect_command_exists(self):
        from keyhole_cli.cli import context_app

        cmd_names = [cmd.name for cmd in context_app.registered_commands]
        assert "inspect" in cmd_names

    def test_run_command_registered_in_main_app(self):
        cmd_names = [cmd.name for cmd in app.registered_commands]
        assert "run" in cmd_names

    def test_runs_app_registered(self):
        from keyhole_cli.cli import runs_app

        assert runs_app is not None

    def test_compile_context_importable_from_sdk(self):
        from keyhole_sdk import compile_context

        assert callable(compile_context)

    def test_inspect_context_importable_from_sdk(self):
        from keyhole_sdk import inspect_context

        assert callable(inspect_context)

    def test_dispatch_run_importable_from_sdk(self):
        from keyhole_sdk import dispatch_run

        assert callable(dispatch_run)


# ─────────────────────────────────────────────────────────────────────────────
# TestProofEmission
# ─────────────────────────────────────────────────────────────────────────────


class TestProofEmission:
    def test_creates_attempted_surface_json(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "client.memory.query", "Forbidden direct memory attempt")
        assert (tmp_path / "memory_boundary" / "attempted-surface.json").exists()

    def test_creates_rejection_json(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.search", "Forbidden")
        assert (tmp_path / "memory_boundary" / "rejection.json").exists()

    def test_creates_summary_md(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.write", "Forbidden write")
        assert (tmp_path / "memory_boundary" / "summary.md").exists()

    def test_attempted_surface_json_has_correct_surface(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "client.memory.upsert", "Forbidden")
        data = json.loads((tmp_path / "memory_boundary" / "attempted-surface.json").read_text())
        assert data["attempted_surface"] == "client.memory.upsert"

    def test_rejection_json_has_error_class(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.get", "Forbidden")
        data = json.loads((tmp_path / "memory_boundary" / "rejection.json").read_text())
        assert data["error_class"] == "DirectMemoryAccessNotAllowed"

    def test_rejection_json_includes_lawful_alternatives(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.delete", "Forbidden")
        data = json.loads((tmp_path / "memory_boundary" / "rejection.json").read_text())
        alternatives = data["lawful_alternatives"]
        assert isinstance(alternatives, list)
        assert any("context compile" in a for a in alternatives)

    def test_rejection_json_boundary_explanation_present(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.query", "Forbidden")
        data = json.loads((tmp_path / "memory_boundary" / "rejection.json").read_text())
        assert "boundary_explanation" in data
        assert len(data["boundary_explanation"]) > 10

    def test_proof_returns_path_dict(self, tmp_path):
        result = emit_memory_boundary_proof(tmp_path, "memory.query", "Forbidden")
        assert "attempted_surface_path" in result
        assert "rejection_path" in result
        assert "summary_path" in result
        assert "correlation_id" in result

    def test_summary_md_mentions_sdk_client_18(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.query", "Forbidden")
        text = (tmp_path / "memory_boundary" / "summary.md").read_text()
        assert "SDK-CLIENT-18" in text

    def test_summary_md_mentions_lawful_alternatives(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.query", "Forbidden")
        text = (tmp_path / "memory_boundary" / "summary.md").read_text()
        assert "context compile" in text

    def test_custom_correlation_id_preserved(self, tmp_path):
        result = emit_memory_boundary_proof(
            tmp_path, "memory.query", "Forbidden", correlation_id="test-corr-123"
        )
        assert result["correlation_id"] == "test-corr-123"
        data = json.loads((tmp_path / "memory_boundary" / "rejection.json").read_text())
        assert data["correlation_id"] == "test-corr-123"

    def test_attempted_surface_json_has_story_field(self, tmp_path):
        emit_memory_boundary_proof(tmp_path, "memory.query", "Forbidden")
        data = json.loads((tmp_path / "memory_boundary" / "attempted-surface.json").read_text())
        assert data["story"] == "SDK-CLIENT-18"


# ─────────────────────────────────────────────────────────────────────────────
# TestMemoryBoundaryPublicSurface
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryBoundaryPublicSurface:
    def test_direct_memory_access_not_allowed_in_all(self):
        assert "DirectMemoryAccessNotAllowed" in keyhole_sdk.__all__

    def test_reject_direct_memory_access_in_all(self):
        assert "reject_direct_memory_access" in keyhole_sdk.__all__

    def test_emit_memory_boundary_proof_in_all(self):
        assert "emit_memory_boundary_proof" in keyhole_sdk.__all__

    def test_get_memory_boundary_repair_in_all(self):
        assert "get_memory_boundary_repair" in keyhole_sdk.__all__

    def test_memory_boundary_rejection_message_in_all(self):
        assert "MEMORY_BOUNDARY_REJECTION_MESSAGE" in keyhole_sdk.__all__

    def test_memory_boundary_lawful_alternatives_in_all(self):
        assert "MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES" in keyhole_sdk.__all__

    def test_memory_boundary_module_importable(self):
        from keyhole_sdk import memory_boundary  # noqa: F401

        assert memory_boundary is not None

    def test_enforcer_module_importable(self):
        from keyhole_sdk.memory_boundary import enforcer  # noqa: F401

        assert enforcer is not None

    def test_proof_module_importable(self):
        from keyhole_sdk.memory_boundary import proof  # noqa: F401

        assert proof is not None


# ─────────────────────────────────────────────────────────────────────────────
# TestMessageQualityRule
# ─────────────────────────────────────────────────────────────────────────────


class TestMessageQualityRule:
    """§8.3: The client must always explain what to do instead, not only what is forbidden."""

    def test_rejection_message_explains_what_to_do_next(self):
        assert "keyhole context compile" in MEMORY_BOUNDARY_REJECTION_MESSAGE

    def test_rejection_message_has_concrete_next_step(self):
        assert "keyhole" in MEMORY_BOUNDARY_REJECTION_MESSAGE

    def test_rejection_message_explains_why(self):
        assert "Why" in MEMORY_BOUNDARY_REJECTION_MESSAGE or "governed" in MEMORY_BOUNDARY_REJECTION_MESSAGE

    def test_rejection_message_starts_with_reject(self):
        assert MEMORY_BOUNDARY_REJECTION_MESSAGE.startswith("REJECT")

    def test_exception_repair_guidance_explains_lawful_path(self):
        with pytest.raises(DirectMemoryAccessNotAllowed) as exc_info:
            reject_direct_memory_access("memory.query")
        guidance = exc_info.value.repair_guidance
        full_text = " ".join(guidance)
        assert "context" in full_text.lower() or "run" in full_text.lower()

    def test_exception_message_not_only_what_forbidden(self):
        exc = DirectMemoryAccessNotAllowed(attempted_surface="memory.search")
        msg = str(exc)
        # Must mention what to do, not just what's forbidden
        assert "governed context" in msg or "governed runs" in msg or "proof" in msg.lower()


# ─────────────────────────────────────────────────────────────────────────────
# TestMemoryBoundaryRejectionMessage
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryBoundaryRejectionMessage:
    def test_rejection_message_is_string(self):
        assert isinstance(MEMORY_BOUNDARY_REJECTION_MESSAGE, str)

    def test_rejection_message_is_non_empty(self):
        assert len(MEMORY_BOUNDARY_REJECTION_MESSAGE) > 50

    def test_lawful_alternatives_is_list_of_strings(self):
        assert isinstance(MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES, list)
        for item in MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES:
            assert isinstance(item, str)

    def test_lawful_alternatives_are_nonempty(self):
        assert len(MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES) >= 3

    def test_alternatives_constant_matches_enforcer_module(self):
        assert MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES == _ALTERNATIVES_FROM_ENFORCER


# ─────────────────────────────────────────────────────────────────────────────
# TestNegativeImportAbsence
# ─────────────────────────────────────────────────────────────────────────────


class TestNegativeImportAbsence:
    """Verify forbidden symbols cannot be imported from the public SDK."""

    def test_cannot_import_memory_query_from_sdk(self):
        with pytest.raises(ImportError):
            from keyhole_sdk import memory_query  # noqa: F401

    def test_cannot_import_memory_write_from_sdk(self):
        with pytest.raises(ImportError):
            from keyhole_sdk import memory_write  # noqa: F401

    def test_cannot_import_memory_search_from_sdk(self):
        with pytest.raises(ImportError):
            from keyhole_sdk import memory_search  # noqa: F401

    def test_cannot_import_memory_client_from_sdk(self):
        with pytest.raises((ImportError, AttributeError)):
            # Either the module raises ImportError or the attribute doesn't exist
            import keyhole_sdk
            _ = keyhole_sdk.memory_query
