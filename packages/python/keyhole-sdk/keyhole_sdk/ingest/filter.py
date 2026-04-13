"""Include/exclude filter — SDK-CLIENT-10 §11.

Deterministic filtering for repository scan. Secret-safe and
conservative by default: excludes .git, .env, node_modules,
build caches, binary artifacts, editor temps, OS junk.
"""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath
from typing import List, Optional, Sequence, Tuple


# ── Default rules (§11) ─────────────────────────────────

DEFAULT_EXCLUDES: List[str] = [
    # VCS internals
    ".git",
    ".git/**",
    ".hg",
    ".hg/**",
    ".svn",
    ".svn/**",
    # Secret / credential files
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    # Virtual environments
    "venv/**",
    ".venv/**",
    "env/**",
    ".tox/**",
    ".nox/**",
    # Node / JS
    "node_modules/**",
    "bower_components/**",
    # Python caches
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".eggs/**",
    "*.egg-info/**",
    # Build output
    "build/**",
    "dist/**",
    "out/**",
    "target/**",
    "bin/**",
    # IDE / editor
    ".idea/**",
    ".vscode/**",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    # Coverage / test caches
    ".coverage",
    "htmlcov/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    # Large binary artifacts
    "*.iso",
    "*.dmg",
    "*.tar.gz",
    "*.tar.bz2",
    "*.zip",
    "*.rar",
    "*.7z",
    "*.jar",
    "*.war",
    "*.ear",
    "*.whl",
    # Docker build context artifacts
    ".docker/**",
]

DEFAULT_INCLUDES: List[str] = [
    # Source
    "*.py",
    "*.js",
    "*.ts",
    "*.jsx",
    "*.tsx",
    "*.java",
    "*.go",
    "*.rs",
    "*.rb",
    "*.c",
    "*.cpp",
    "*.h",
    "*.hpp",
    "*.cs",
    "*.swift",
    "*.kt",
    "*.scala",
    "*.sh",
    "*.bash",
    "*.zsh",
    "*.sql",
    "*.html",
    "*.css",
    "*.scss",
    "*.less",
    "*.vue",
    "*.svelte",
    # Docs
    "*.md",
    "*.rst",
    "*.txt",
    "*.adoc",
    # Config / manifests
    "*.json",
    "*.yaml",
    "*.yml",
    "*.toml",
    "*.cfg",
    "*.ini",
    "*.xml",
    "*.gradle",
    "*.properties",
    # Build / CI
    "Makefile",
    "Dockerfile",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "Jenkinsfile",
    "Vagrantfile",
    "Procfile",
    ".github/**",
    ".gitlab-ci.yml",
    # Lock files (useful for dependency scanning)
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "Pipfile.lock",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
]


class IncludeExcludeFilter:
    """Deterministic include/exclude filter for repo scanning (§11).

    - Exclusion rules take priority over inclusion rules.
    - Builder-supplied overrides supplement but do not eliminate defaults.
    """

    def __init__(
        self,
        *,
        extra_includes: Optional[Sequence[str]] = None,
        extra_excludes: Optional[Sequence[str]] = None,
    ) -> None:
        self._excludes = list(DEFAULT_EXCLUDES)
        if extra_excludes:
            self._excludes.extend(extra_excludes)

        self._includes = list(DEFAULT_INCLUDES)
        if extra_includes:
            self._includes.extend(extra_includes)

    @property
    def exclude_rules(self) -> List[str]:
        return list(self._excludes)

    @property
    def include_rules(self) -> List[str]:
        return list(self._includes)

    def classify(self, rel_path: str) -> Tuple[bool, str]:
        """Classify a relative path as (included, reason).

        Returns (True, "include") if the file passes, or
        (False, "exclude:<rule>") if excluded.
        """
        # Normalize to forward-slash
        norm = rel_path.replace("\\", "/")

        # Check exclusion first (priority)
        for pattern in self._excludes:
            if self._matches(norm, pattern):
                return False, f"exclude:{pattern}"

        # Check inclusion
        for pattern in self._includes:
            if self._matches(norm, pattern):
                return True, "include"

        # Default: exclude unknown file types for safety
        return False, "exclude:no_matching_include"

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        """Match a relative path against a glob pattern.

        Supports directory patterns (e.g. '.git/**') and
        filename patterns (e.g. '*.pyc').
        """
        # Direct segment match (e.g. ".git" matches ".git" as a path component)
        parts = PurePosixPath(path).parts
        pattern_parts = PurePosixPath(pattern).parts

        # Simple filename pattern matching
        name = PurePosixPath(path).name
        if fnmatch.fnmatch(name, pattern):
            return True

        # Full path pattern matching
        if fnmatch.fnmatch(path, pattern):
            return True

        # Check if any path component matches a directory-level pattern
        # e.g. pattern ".git" should match ".git/config"
        if not pattern.endswith("/**") and "/" not in pattern and "*" not in pattern:
            if pattern in parts:
                return True

        # Pattern like "dir/**" matches "dir/anything"
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if path.startswith(prefix + "/") or path == prefix:
                return True
            # Also match if any parent component equals the prefix
            if prefix in parts:
                return True

        return False
