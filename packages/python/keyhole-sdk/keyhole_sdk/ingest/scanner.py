"""Local repository scanner — SDK-CLIENT-10 §8.

Deterministic inspection of a local repository. Reads files,
classifies them, detects language/framework signals, and reports
topology. Never mutates the target repo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Sequence

from keyhole_sdk.ingest.filter import IncludeExcludeFilter
from keyhole_sdk.ingest.models import (
    ConfidenceLevel,
    FileClassification,
    RepoScanResult,
    ScanSignal,
)


# ── Manifest → Language/Framework map ────────────────────

_MANIFEST_SIGNALS: dict[str, tuple[str, str]] = {
    "pyproject.toml": ("python", ""),
    "setup.py": ("python", ""),
    "setup.cfg": ("python", ""),
    "requirements.txt": ("python", ""),
    "Pipfile": ("python", ""),
    "poetry.lock": ("python", ""),
    "package.json": ("javascript", ""),
    "tsconfig.json": ("typescript", ""),
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java", "gradle"),
    "build.gradle.kts": ("kotlin", "gradle"),
    "go.mod": ("go", ""),
    "Cargo.toml": ("rust", "cargo"),
    "Gemfile": ("ruby", ""),
    "composer.json": ("php", ""),
    "mix.exs": ("elixir", ""),
    "Package.swift": ("swift", ""),
    "*.csproj": ("csharp", "dotnet"),
    "*.fsproj": ("fsharp", "dotnet"),
    "CMakeLists.txt": ("c/cpp", "cmake"),
    "Makefile": ("", "make"),
}

_FRAMEWORK_HINTS: dict[str, str] = {
    "manage.py": "django",
    "next.config.js": "nextjs",
    "next.config.ts": "nextjs",
    "nuxt.config.js": "nuxt",
    "nuxt.config.ts": "nuxt",
    "angular.json": "angular",
    "svelte.config.js": "svelte",
    "astro.config.mjs": "astro",
    "vite.config.ts": "vite",
    "vite.config.js": "vite",
    "webpack.config.js": "webpack",
    "tailwind.config.js": "tailwind",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
}

_SOURCE_DIR_NAMES = {"src", "app", "lib", "pkg", "cmd", "internal", "backend", "frontend", "api", "core"}
_TEST_DIR_NAMES = {"tests", "test", "spec", "specs", "__tests__", "test_utils", "testing"}
_DOC_DIR_NAMES = {"docs", "doc", "documentation", "wiki"}

_KEYHOLE_MARKERS = {"keyhole.yaml", "governance_contract.yaml", "capability_passport.yaml"}


def scan_repo(
    repo_path: str | Path,
    *,
    file_filter: Optional[IncludeExcludeFilter] = None,
    max_bytes: int = 0,
) -> RepoScanResult:
    """Scan a local repository deterministically (§8).

    This function:
    1. Walks the repo tree
    2. Applies include/exclude filtering
    3. Detects language/framework signals
    4. Classifies files and directories
    5. Returns a structured scan result

    Never mutates the target repository.

    Args:
        repo_path: Absolute or relative path to the repository root.
        file_filter: An IncludeExcludeFilter instance. Defaults to standard rules.
        max_bytes: Maximum total bytes to include (0 = unlimited).

    Returns:
        RepoScanResult with all observed facts.
    """
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repository path does not exist or is not a directory: {root}")

    if file_filter is None:
        file_filter = IncludeExcludeFilter()

    languages: set[str] = set()
    frameworks: set[str] = set()
    manifests: list[str] = []
    source_dirs: set[str] = set()
    test_dirs: set[str] = set()
    doc_files: list[str] = []
    build_files: list[str] = []
    included_files: list[str] = []
    excluded_files: list[str] = []
    signals: list[ScanSignal] = []
    total_files = 0
    total_included_bytes = 0
    has_keyhole = False

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Skip excluded directories early for performance
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""

        # Prune excluded directories
        kept_dirs: list[str] = []
        for d in dirnames:
            dir_rel = f"{rel_dir}/{d}" if rel_dir else d
            # Check if the directory itself is explicitly excluded
            # (e.g. ".git", "node_modules", "venv", "__pycache__")
            # Only prune if the directory name matches a non-glob exclude pattern
            # or the directory path matches a directory-level exclude pattern
            is_excluded = False
            for pattern in file_filter.exclude_rules:
                # Directory-level patterns like ".git", "venv/**", "node_modules/**"
                if IncludeExcludeFilter._matches(dir_rel, pattern):
                    is_excluded = True
                    break
                if IncludeExcludeFilter._matches(dir_rel + "/", pattern):
                    is_excluded = True
                    break
            if not is_excluded:
                kept_dirs.append(d)
        dirnames[:] = sorted(kept_dirs)

        # Classify directory
        dir_name = os.path.basename(dirpath)
        if dir_name in _SOURCE_DIR_NAMES and rel_dir:
            source_dirs.add(rel_dir)
        if dir_name in _TEST_DIR_NAMES and rel_dir:
            test_dirs.add(rel_dir)

        for filename in sorted(filenames):
            rel_path = f"{rel_dir}/{filename}" if rel_dir else filename
            total_files += 1

            # Include/exclude check
            included, reason = file_filter.classify(rel_path)
            if not included:
                excluded_files.append(rel_path)
                continue

            # Size check
            try:
                file_size = os.path.getsize(os.path.join(dirpath, filename))
            except OSError:
                file_size = 0

            if max_bytes > 0 and total_included_bytes + file_size > max_bytes:
                excluded_files.append(rel_path)
                continue

            total_included_bytes += file_size
            included_files.append(rel_path)

            # Keyhole scaffold detection
            if filename in _KEYHOLE_MARKERS:
                has_keyhole = True

            # Manifest detection
            if filename in _MANIFEST_SIGNALS:
                lang, fw = _MANIFEST_SIGNALS[filename]
                manifests.append(rel_path)
                if lang:
                    languages.add(lang)
                    signals.append(ScanSignal(
                        kind="language",
                        path=rel_path,
                        value=lang,
                        confidence=ConfidenceLevel.HIGH,
                    ))
                if fw:
                    frameworks.add(fw)
                    signals.append(ScanSignal(
                        kind="framework",
                        path=rel_path,
                        value=fw,
                        confidence=ConfidenceLevel.HIGH,
                    ))

            # Framework hint detection
            if filename in _FRAMEWORK_HINTS:
                fw = _FRAMEWORK_HINTS[filename]
                frameworks.add(fw)
                signals.append(ScanSignal(
                    kind="framework",
                    path=rel_path,
                    value=fw,
                    confidence=ConfidenceLevel.MEDIUM,
                ))

            # File classification
            classification = _classify_file(rel_path, filename)

            if classification == FileClassification.DOC:
                doc_files.append(rel_path)
            elif classification == FileClassification.BUILD:
                build_files.append(rel_path)
            elif classification == FileClassification.CI:
                build_files.append(rel_path)

    # Language inference from file extensions as a fallback
    _infer_languages_from_extensions(included_files, languages, signals)

    return RepoScanResult(
        repo_root=str(root),
        languages=sorted(languages),
        frameworks=sorted(frameworks),
        manifests=sorted(manifests),
        source_dirs=sorted(source_dirs),
        test_dirs=sorted(test_dirs),
        doc_files=sorted(doc_files),
        build_files=sorted(build_files),
        included_files=sorted(included_files),
        excluded_files=sorted(excluded_files),
        signals=sorted(signals, key=lambda s: (s.kind, s.path)),
        total_files=total_files,
        total_included_bytes=total_included_bytes,
        has_keyhole_scaffold=has_keyhole,
    )


def _classify_file(rel_path: str, filename: str) -> FileClassification:
    """Classify a file based on its name and location."""
    lower = filename.lower()

    # Docs
    if lower in ("readme.md", "readme.rst", "readme.txt", "readme", "changelog.md",
                 "contributing.md", "license", "license.md", "license.txt"):
        return FileClassification.DOC
    if lower.endswith((".md", ".rst", ".adoc")) and "doc" in rel_path.lower():
        return FileClassification.DOC

    # Build/CI
    if lower in ("dockerfile", "makefile", "jenkinsfile", "vagrantfile", "procfile"):
        return FileClassification.BUILD
    if lower.startswith("docker-compose"):
        return FileClassification.BUILD
    if ".github/" in rel_path or ".gitlab-ci" in lower:
        return FileClassification.CI

    # Manifests / dependency
    if lower in _MANIFEST_SIGNALS:
        return FileClassification.MANIFEST

    # Config
    if lower.endswith((".yaml", ".yml", ".toml", ".cfg", ".ini", ".json")) and "config" in lower:
        return FileClassification.CONFIG

    # Test
    parts = rel_path.split("/")
    for part in parts:
        if part in _TEST_DIR_NAMES:
            return FileClassification.TEST
    if lower.startswith("test_") or lower.endswith("_test.py") or lower.endswith(".test.js"):
        return FileClassification.TEST

    # Source
    if lower.endswith((".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp",
                       ".h", ".hpp", ".cs", ".swift", ".kt")):
        return FileClassification.SOURCE

    return FileClassification.OTHER


_EXT_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".c": "c",
    ".cpp": "c++",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".php": "php",
    ".sh": "shell",
    ".sql": "sql",
}


def _infer_languages_from_extensions(
    files: list[str],
    languages: set[str],
    signals: list[ScanSignal],
) -> None:
    """Infer additional languages from file extensions (low confidence)."""
    seen: set[str] = set()
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        lang = _EXT_LANGUAGE_MAP.get(ext)
        if lang and lang not in languages and lang not in seen:
            seen.add(lang)
            languages.add(lang)
            signals.append(ScanSignal(
                kind="language",
                path=f,
                value=lang,
                confidence=ConfidenceLevel.LOW,
            ))
