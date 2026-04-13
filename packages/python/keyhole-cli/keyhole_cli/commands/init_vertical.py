"""`keyhole init vertical` — deterministic governed repo scaffold generation.

SDK-CLIENT-02: Creates a canonical governed participant repository with
declaration artifacts, context-ready placeholders, and proof-ready structure.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE, EXIT_INVALID_INPUT


# ──────────────────────────────────────────────────────────────
# Schema version — referenced by all generated declaration files
# ──────────────────────────────────────────────────────────────
SCHEMA_VERSION = "v0.1"

# Files that are managed by the scaffold and may be overwritten with --force
MANAGED_FILES = {
    "keyhole.yaml",
    "governance_contract.yaml",
    "capability_passport.yaml",
    "dependencies.yaml",
    "docs/README.md",
    "proof_bundle/README.md",
    "context/README.md",
    ".keyhole/README.md",
}

# Directories with .gitkeep placeholders
MANAGED_DIRS = [
    "capabilities",
    "src",
    "tests",
    "docs/context",
    "proof_bundle/core",
    "proof_bundle/extended",
    "context/requests",
    "context/resolved",
    ".keyhole/state",
    ".keyhole/cache",
]


# ──────────────────────────────────────────────────────────────
# Template content generators — deterministic for same inputs
# ──────────────────────────────────────────────────────────────


def _render_keyhole_yaml(repo_name: str, timestamp: str) -> str:
    """Render keyhole.yaml — local repo identity and scaffold metadata."""
    return (
        f"schema_version: {SCHEMA_VERSION}\n"
        f"repo:\n"
        f"  name: {repo_name}\n"
        f"  kind: vertical\n"
        f"  owner: Keyhole Solution Foundation\n"
        f"  visibility: private\n"
        f"sdk:\n"
        f"  initialized_by: keyhole init vertical\n"
        f"  initialized_at: \"{timestamp}\"\n"
        f"  template: default\n"
        f"context:\n"
        f"  mode: explicit\n"
        f"proof:\n"
        f"  enabled: true\n"
    )


def _render_governance_contract(repo_name: str) -> str:
    """Render governance_contract.yaml — local governance declaration."""
    return (
        f"schema_version: {SCHEMA_VERSION}\n"
        f"repo: {repo_name}\n"
        f"parent_repo: null\n"
        f"produces: []\n"
        f"required_tests: []\n"
        f"local_invariants: []\n"
        f"compatibility_contracts: []\n"
    )


def _render_capability_passport(repo_name: str) -> str:
    """Render capability_passport.yaml — future portable capability identity."""
    return (
        f"schema_version: {SCHEMA_VERSION}\n"
        f"capabilities: []\n"
        f"owner_repo: {repo_name}\n"
        f"visibility: private\n"
        f"proofs: []\n"
        f"trust:\n"
        f"  sbom_digest: null\n"
        f"  attestation_digest: null\n"
        f"  transparency_ref: null\n"
    )


def _render_dependencies() -> str:
    """Render dependencies.yaml — upstream capability dependencies."""
    return (
        f"schema_version: {SCHEMA_VERSION}\n"
        f"dependencies: []\n"
    )


def _render_docs_readme(repo_name: str) -> str:
    """Render docs/README.md — human-readable scaffold overview."""
    return (
        f"# {repo_name}\n"
        f"\n"
        f"This repository was scaffolded by `keyhole init vertical`.\n"
        f"\n"
        f"## Generated Declaration Files\n"
        f"\n"
        f"| File | Purpose |\n"
        f"|------|---------|\n"
        f"| `keyhole.yaml` | Local repo identity, scaffold metadata, and future registration anchor |\n"
        f"| `governance_contract.yaml` | Local governance rules, produced capabilities, required tests, and invariants |\n"
        f"| `capability_passport.yaml` | Future portable capability / proof identity placeholder |\n"
        f"| `dependencies.yaml` | Declared upstream capability dependencies |\n"
        f"\n"
        f"## Important\n"
        f"\n"
        f"This scaffold is **local only**. Generating it does not register this\n"
        f"repository with the MCP boundary, does not create governed proof, and\n"
        f"does not imply live platform participation.\n"
        f"\n"
        f"## Next Steps\n"
        f"\n"
        f"1. `keyhole validate` — validate local declaration files\n"
        f"2. Edit `governance_contract.yaml` — declare capabilities and invariants\n"
        f"3. Edit `capability_passport.yaml` — declare capabilities\n"
        f"4. `keyhole repo register` — register with the MCP boundary (later)\n"
        f"5. `keyhole context compile` — compile governed context (later)\n"
        f"6. `keyhole run --context auto` — execute a governed run (later)\n"
    )


def _render_proof_readme() -> str:
    """Render proof_bundle/README.md — proof-ready structure explanation."""
    return (
        "# Proof Bundle\n"
        "\n"
        "This directory holds proof artifacts generated by governed workflows.\n"
        "\n"
        "## Structure\n"
        "\n"
        "- `core/` — Replay-critical hot proof artifacts (core.json, summary.md, etc.)\n"
        "- `extended/` — Large or secondary evidence referenced by digest\n"
        "\n"
        "## Hot vs Extended\n"
        "\n"
        "The split ensures that replay-critical truth stays on the hot path while\n"
        "large auxiliary evidence lives in referenced cold storage. Replay must\n"
        "succeed from core artifacts alone.\n"
        "\n"
        "## Status\n"
        "\n"
        "These directories are placeholders created by `keyhole init vertical`.\n"
        "They will be populated by later governed run and proof workflows.\n"
    )


def _render_context_readme() -> str:
    """Render context/README.md — context-ready placeholder explanation."""
    return (
        "# Context\n"
        "\n"
        "This directory supports governed context lifecycle workflows.\n"
        "\n"
        "## Structure\n"
        "\n"
        "- `requests/` — Local staging area for context request artifacts\n"
        "- `resolved/` — Resolved context references or summaries\n"
        "\n"
        "## Important\n"
        "\n"
        "Governed execution requires explicit governed context. This directory\n"
        "prepares the repo for later context-bound runs.\n"
        "\n"
        "This scaffold does **not** perform context compilation. Context will be\n"
        "compiled through `keyhole context compile` in a later workflow.\n"
    )


def _render_keyhole_readme() -> str:
    """Render .keyhole/README.md — tool-managed state explanation."""
    return (
        "# .keyhole\n"
        "\n"
        "This directory is managed by the Keyhole CLI and SDK.\n"
        "\n"
        "## Structure\n"
        "\n"
        "- `state/` — Local tool-managed state artifacts\n"
        "- `cache/` — Temporary cache data\n"
        "\n"
        "## Warning\n"
        "\n"
        "This directory is **not** authoritative platform truth. It contains\n"
        "local convenience state only. Do not depend on its contents for\n"
        "governance decisions or proof claims.\n"
        "\n"
        "The authoritative source of truth is always the MCP boundary.\n"
    )


# ──────────────────────────────────────────────────────────────
# Scaffold plan and execution
# ──────────────────────────────────────────────────────────────


def _build_file_plan(
    repo_name: str,
    timestamp: str,
) -> Dict[str, str]:
    """Build deterministic map of relative path -> file content."""
    return {
        "keyhole.yaml": _render_keyhole_yaml(repo_name, timestamp),
        "governance_contract.yaml": _render_governance_contract(repo_name),
        "capability_passport.yaml": _render_capability_passport(repo_name),
        "dependencies.yaml": _render_dependencies(),
        "docs/README.md": _render_docs_readme(repo_name),
        "proof_bundle/README.md": _render_proof_readme(),
        "context/README.md": _render_context_readme(),
        ".keyhole/README.md": _render_keyhole_readme(),
    }


def _detect_existing_scaffold(base: Path) -> bool:
    """Return True if the target directory already has a keyhole.yaml."""
    return (base / "keyhole.yaml").exists()


def _find_conflicts(base: Path, file_plan: Dict[str, str]) -> List[str]:
    """Find managed files that already exist on disk."""
    conflicts = []
    for rel_path in file_plan:
        target = base / rel_path
        if target.exists():
            conflicts.append(rel_path)
    return sorted(conflicts)


def _compute_plan_digest(file_plan: Dict[str, str]) -> str:
    """Compute a deterministic digest over all managed file content."""
    h = hashlib.sha256()
    for key in sorted(file_plan.keys()):
        h.update(key.encode("utf-8"))
        h.update(file_plan[key].encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


def _execute_scaffold(
    base: Path,
    file_plan: Dict[str, str],
    force: bool,
) -> Tuple[List[str], List[str], List[str]]:
    """Write scaffold to disk. Returns (created, skipped, errors)."""
    created: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    # Create directories with .gitkeep
    for dir_rel in MANAGED_DIRS:
        dir_path = base / dir_rel
        dir_path.mkdir(parents=True, exist_ok=True)
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            try:
                gitkeep.write_text("", encoding="utf-8")
            except OSError as exc:
                errors.append(f"Could not create {dir_rel}/.gitkeep: {exc}")

    # Write managed files
    for rel_path, content in sorted(file_plan.items()):
        target = base / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not force:
            skipped.append(rel_path)
            continue

        try:
            target.write_text(content, encoding="utf-8")
            created.append(rel_path)
        except OSError as exc:
            errors.append(f"Could not write {rel_path}: {exc}")

    return created, skipped, errors


# ──────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────


def run_init_vertical(
    *,
    name: str = "",
    path: str = "",
    force: bool = False,
    dry_run: bool = False,
    template: str = "default",
    non_interactive: bool = False,
) -> CommandResult:
    """Generate a canonical governed participant repo scaffold.

    This is a local-only, offline-safe operation. It does not contact
    the MCP boundary or claim governed participation.
    """
    # Validate template
    if template != "default":
        return CommandResult(
            command="init vertical",
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            data={"error": "invalid_template", "template": template},
            warnings=[f"Unknown template: {template}. Only 'default' is supported."],
            next_steps=["Use --template default or omit the flag."],
            summary=f"Invalid template: {template}",
        )

    # Resolve target directory
    if path:
        base = Path(path).resolve()
    elif name:
        base = Path.cwd().resolve() / name
    else:
        return CommandResult(
            command="init vertical",
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            data={"error": "missing_name"},
            warnings=["No repo name or path specified."],
            next_steps=[
                "Provide a name: keyhole init vertical <name>",
                "Or specify a path: keyhole init vertical --path <dir>",
            ],
            summary="No repo name or path specified",
        )

    repo_name = name if name else base.name
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build deterministic file plan
    file_plan = _build_file_plan(repo_name, timestamp)
    plan_digest = _compute_plan_digest(file_plan)

    # Dry-run mode
    if dry_run:
        tree_lines = _format_tree(file_plan)
        return CommandResult(
            command="init vertical",
            success=True,
            exit_code=EXIT_SUCCESS,
            data={
                "dry_run": True,
                "target_path": str(base),
                "repo_name": repo_name,
                "template": template,
                "managed_files": sorted(file_plan.keys()),
                "managed_dirs": sorted(MANAGED_DIRS),
                "plan_digest": plan_digest,
                "tree": tree_lines,
            },
            next_steps=["Remove --dry-run to create the scaffold."],
            summary=f"Dry run: would create {len(file_plan)} files and {len(MANAGED_DIRS)} directories in {base}",
        )

    # Detect existing scaffold without --force
    if _detect_existing_scaffold(base) and not force:
        conflicts = _find_conflicts(base, file_plan)
        return CommandResult(
            command="init vertical",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "error": "already_initialized",
                "target_path": str(base),
                "existing_files": conflicts,
            },
            warnings=[
                f"Directory already contains a governed scaffold: {base}",
                f"Found {len(conflicts)} existing managed file(s).",
            ],
            next_steps=[
                "Use --force to overwrite managed scaffold files.",
                "Use --dry-run to inspect what would change.",
            ],
            summary=f"Already initialized: {base}",
        )

    # Validate target path
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return CommandResult(
            command="init vertical",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"error": "path_error", "target_path": str(base), "detail": str(exc)},
            warnings=[f"Cannot create directory: {exc}"],
            next_steps=["Check the target path and permissions."],
            summary=f"Path error: {exc}",
        )

    # Execute scaffold
    created, skipped, errors = _execute_scaffold(base, file_plan, force=force)

    if errors:
        return CommandResult(
            command="init vertical",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "target_path": str(base),
                "repo_name": repo_name,
                "created": created,
                "skipped": skipped,
                "errors": errors,
            },
            warnings=errors,
            next_steps=["Fix the errors above and retry."],
            summary=f"Scaffold failed: {len(errors)} error(s)",
        )

    mode = "forced" if force and skipped == [] and _detect_existing_scaffold(base) else "fresh"
    if force and any(f in created for f in MANAGED_FILES):
        mode = "forced"

    return CommandResult(
        command="init vertical",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "target_path": str(base),
            "repo_name": repo_name,
            "template": template,
            "mode": mode,
            "created": created,
            "skipped": skipped,
            "plan_digest": plan_digest,
        },
        next_steps=[
            "keyhole validate",
            "Edit governance_contract.yaml to declare capabilities and invariants.",
            "Edit capability_passport.yaml to declare capabilities.",
            "Later: keyhole repo register",
        ],
        summary=(
            f"Governed repo scaffold created: {base}"
            if mode == "fresh"
            else f"Governed repo scaffold updated (--force): {base}"
        ),
    )


def _format_tree(file_plan: Dict[str, str]) -> List[str]:
    """Build a simple tree representation for dry-run output."""
    all_paths: List[str] = []
    for rel in sorted(file_plan.keys()):
        all_paths.append(rel)
    for d in sorted(MANAGED_DIRS):
        all_paths.append(f"{d}/.gitkeep")
    return sorted(set(all_paths))
