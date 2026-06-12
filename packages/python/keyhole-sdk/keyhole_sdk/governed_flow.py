"""Generic governed repository flow for forked SDK/client repos."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from keyhole_sdk.governed_demo import (
    GovernedDemoError,
    GovernedFirstAppClient,
    _file_digest,
    _load_yaml,
    _repo_git_metadata,
    _redact,
)
from keyhole_sdk.models import GovernanceReceipt


GENERIC_GAP_ID_OVERRIDE_ENV = "KEYHOLE_GOVERNED_GAP_ID"


@dataclass
class RepoDeclaration:
    repo_dir: Path
    repo_name: str
    repo_remote: str
    commit_sha: str
    branch: str = ""
    repo_class: str = ""
    story_id: str = ""
    capability_id: str = ""
    declaration_file_digests: Dict[str, str] = field(default_factory=dict)
    native_artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class GovernedRepoFlowClient(GovernedFirstAppClient):
    """Reusable governed flow client for arbitrary forked repositories."""

    def __init__(
        self,
        *,
        mcp_url: str,
        token: str,
        runtime_url: str = "http://localhost:8080",
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
        story_id: str = "",
        capability_id: str = "",
        repo_class: str = "",
        gap_id: str = "",
    ) -> None:
        super().__init__(
            mcp_url=mcp_url,
            token=token,
            runtime_url=runtime_url,
            session=session,
            timeout=timeout,
            story_id=story_id,
            capability_id=capability_id,
            repo_class=repo_class,
            gap_override_env=GENERIC_GAP_ID_OVERRIDE_ENV,
            purpose="generic governed forked SDK repo flow",
        )
        self.operator_gap_id = gap_id
        self.repo_declaration: Optional[RepoDeclaration] = None

    @classmethod
    def from_env(
        cls,
        *,
        runtime_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        story_id: str = "",
        capability_id: str = "",
        repo_class: str = "",
        gap_id: str = "",
    ) -> "GovernedRepoFlowClient":
        return cls(
            mcp_url=os.environ.get("KEYHOLE_MCP_URL", ""),
            token=os.environ.get("KEYHOLE_MCP_TOKEN", ""),
            runtime_url=runtime_url or os.environ.get("KEYHOLE_RUNTIME_URL", "http://localhost:8080"),
            session=session,
            story_id=story_id,
            capability_id=capability_id,
            repo_class=repo_class,
            gap_id=gap_id,
        )

    def inspect_repo(self, repo_path: str | Path) -> RepoDeclaration:
        repo = Path(repo_path).resolve()
        declaration = read_repo_declaration(
            repo,
            story_id=self.story_id,
            capability_id=self.capability_id,
            repo_class=self.repo_class,
        )
        self.repo_declaration = declaration
        self.story_id = declaration.story_id
        self.gap_label = declaration.story_id
        self.capability_id = declaration.capability_id
        self.repo_class = declaration.repo_class
        return declaration

    def run_governed_repo_flow(
        self,
        repo_dir: str | Path,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        declaration = self.inspect_repo(repo_dir)
        self.discover()
        if dry_run:
            gap_id = self.operator_gap_id or self._resolve_gap_id(declaration.repo_dir)
            return {
                "dry_run": True,
                "repo": _public_declaration(declaration),
                "resolved_gap_id": gap_id,
                "gap_id_source": self.gap_id_source,
                "would_mutate_mcp": False,
            }
        registration = self.register_repo(declaration.repo_dir)
        context = self.compile_context(declaration.repo_dir)
        receipt = self.run_governed_realization(declaration.repo_dir)
        return {
            "dry_run": False,
            "repo": _public_declaration(declaration),
            "resolved_gap_id": registration.get("gap_id", self.resolved_gap_id),
            "gap_id_source": registration.get("gap_id_source", self.gap_id_source),
            "claim_id": registration.get("claim_id", ""),
            "claim_ref": registration.get("claim_ref", ""),
            "registration_id": registration.get("registration_id", ""),
            "governance_context_id": context.get("governance_context_id", ""),
            "receipt": receipt.model_dump(mode="json"),
        }

    def _resolve_gap_id(self, repo: Path) -> str:
        if self.operator_gap_id:
            if not self.operator_gap_id.startswith("gap_"):
                raise GovernedDemoError("--gap-id must be a canonical gap_* id.")
            self.resolved_gap_id = self.operator_gap_id
            self.gap_id_source = "operator --gap-id"
            return self.operator_gap_id
        return super()._resolve_gap_id(repo)


def run_governed_repo_flow(
    *,
    repo_dir: str | Path,
    mcp_url: str,
    token: str,
    runtime_url: str = "http://localhost:8080",
    story_id: str = "",
    capability_id: str = "",
    repo_class: str = "",
    gap_id: str = "",
    dry_run: bool = False,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    client = GovernedRepoFlowClient(
        mcp_url=mcp_url,
        token=token,
        runtime_url=runtime_url,
        story_id=story_id,
        capability_id=capability_id,
        repo_class=repo_class,
        gap_id=gap_id,
        session=session,
    )
    return client.run_governed_repo_flow(repo_dir, dry_run=dry_run)


def read_repo_declaration(
    repo: Path,
    *,
    story_id: str = "",
    capability_id: str = "",
    repo_class: str = "",
) -> RepoDeclaration:
    required = ["keyhole.yaml", "governance_contract.yaml", "capability_passport.yaml", "dependencies.yaml"]
    missing = [name for name in required if not (repo / name).exists()]
    if missing:
        raise GovernedDemoError("missing governance declaration file(s): " + ", ".join(missing))
    keyhole = _load_yaml(repo / "keyhole.yaml")
    contract = _load_yaml(repo / "governance_contract.yaml")
    passport = _load_yaml(repo / "capability_passport.yaml")
    dependencies = _load_yaml(repo / "dependencies.yaml")
    metadata = _repo_git_metadata(repo)
    derived_capability = capability_id or _first_capability(contract, passport)
    if not derived_capability:
        raise GovernedDemoError("cannot derive capability_id from declaration files; pass --capability-id.")
    derived_repo_class = repo_class or str(keyhole.get("repo_class") or keyhole.get("kind") or "")
    if not derived_repo_class:
        repo_meta = keyhole.get("repo_meta") if isinstance(keyhole.get("repo_meta"), dict) else {}
        derived_repo_class = str(repo_meta.get("kind") or "")
    if derived_repo_class.lower() == "vertical":
        derived_repo_class = "SDK_TEMPLATE"
    if not derived_repo_class:
        raise GovernedDemoError("cannot derive repo_class from declaration files; pass --repo-class.")
    derived_story_id = story_id or str(keyhole.get("story_id") or contract.get("story_id") or "")
    return RepoDeclaration(
        repo_dir=repo,
        repo_name=str(keyhole.get("repo") or repo.name),
        repo_remote=metadata["repo_remote"],
        commit_sha=metadata["commit_sha"],
        branch=metadata.get("branch", ""),
        repo_class=derived_repo_class,
        story_id=derived_story_id,
        capability_id=derived_capability,
        declaration_file_digests={
            "keyhole_yaml_digest": _file_digest(repo / "keyhole.yaml"),
            "governance_contract_digest": _file_digest(repo / "governance_contract.yaml"),
            "capability_passport_digest": _file_digest(repo / "capability_passport.yaml"),
            "dependencies_digest": _file_digest(repo / "dependencies.yaml"),
        },
        native_artifacts={
            "keyhole": keyhole,
            "governance_contract": contract,
            "capability_passport": passport,
            "dependencies": dependencies,
        },
    )


def _first_capability(contract: Dict[str, Any], passport: Dict[str, Any]) -> str:
    produces = contract.get("produces") if isinstance(contract.get("produces"), list) else []
    if produces:
        return str(produces[0])
    capabilities = passport.get("capabilities") if isinstance(passport.get("capabilities"), list) else []
    for capability in capabilities:
        if isinstance(capability, dict):
            name = str(capability.get("name") or capability.get("capability") or "")
            if name:
                return name
    return str(passport.get("capability") or "")


def _public_declaration(declaration: RepoDeclaration) -> Dict[str, Any]:
    return _redact({
        "repo_name": declaration.repo_name,
        "repo_remote": declaration.repo_remote,
        "commit_sha": declaration.commit_sha,
        "branch": declaration.branch,
        "repo_class": declaration.repo_class,
        "story_id": declaration.story_id,
        "capability_id": declaration.capability_id,
        "declaration_file_digests": declaration.declaration_file_digests,
    })
