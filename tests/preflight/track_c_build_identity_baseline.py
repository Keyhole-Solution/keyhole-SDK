"""
CE-V5-S51-CUTOVER-C-01: Reproducible Build Identity Baseline

Preflight measurement script.

Phase 1 (SDK-side, no Docker required):
  - Captures git state
  - Hashes all build inputs: Dockerfile, requirements.txt, app/ source manifest
  - Performs static non-determinism analysis
  - Reports static verdict and emits a baseline JSON artifact

Phase 2 (Docker required — run on Linux CI host or manually):
  - Build from source with --no-cache
  - Compare built digest to canonical sha256:a9af9cc5
  - Record base image resolved digest, pip version, platform
  - Emit signed delta report if digests differ

Usage:
    # Phase 1 only (always safe to run):
    python tests/preflight/track_c_build_identity_baseline.py

    # Phase 2 (requires Docker):
    CANONICAL_DIGEST=sha256:a9af9cc5... \\
    RUN_DOCKER_BUILD=1 \\
    python tests/preflight/track_c_build_identity_baseline.py

Outputs:
    docs/evidence/cutover-c-01/build_identity_baseline.json
    docs/evidence/cutover-c-01/static_nondet_analysis.json
    docs/evidence/cutover-c-01/delta_report.json  (Phase 2 only)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "services" / "test-runtime"
APP_DIR = RUNTIME_DIR / "app"
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence" / "cutover-c-01"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

STORY_ID = "CE-V5-S51-CUTOVER-C-01"
GAP_ID = "gap_b4bcf14ab2e95b1b"
# Production canonical digest — this is the TARGET for reproduction
CANONICAL_DIGEST = os.environ.get(
    "CANONICAL_DIGEST",
    "sha256:a9af9cc5",  # short prefix; full digest recorded by platform
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "UNKNOWN"


def git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--short"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
        return bool(out)
    except Exception:
        return True


def git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "UNKNOWN"


def now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Phase 1: Static build input capture
# ---------------------------------------------------------------------------

def capture_source_manifest() -> dict[str, str]:
    """SHA-256 hash of every file in services/test-runtime/ recursively."""
    manifest: dict[str, str] = {}
    for path in sorted(RUNTIME_DIR.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            manifest[rel] = sha256_file(path)
    return manifest


def analyze_dockerfile_determinism(dockerfile: Path) -> dict[str, Any]:
    """
    Static analysis of Dockerfile for non-deterministic inputs.
    Returns a structured report of each factor.
    """
    content = dockerfile.read_text(encoding="utf-8")
    factors: list[dict] = []

    # 1. Base image tag — is it pinned to a digest?
    from_match = re.search(r"^FROM\s+(\S+)", content, re.MULTILINE)
    if from_match:
        from_value = from_match.group(1)
        pinned = "@sha256:" in from_value
        factors.append({
            "factor": "base_image",
            "value": from_value,
            "deterministic": pinned,
            "issue": None if pinned else "Mutable tag — must pin to digest for reproducibility",
            "repair": "FROM python:3.11-slim@sha256:<digest>",
        })

    # 2. pip install — hash verification?
    pip_match = re.search(r"pip install\s+(.+)", content)
    if pip_match:
        pip_args = pip_match.group(1).strip()
        hash_verified = "--require-hashes" in pip_args
        factors.append({
            "factor": "pip_install",
            "value": pip_args,
            "deterministic": hash_verified,
            "issue": None if hash_verified else (
                "pip install without --require-hashes — wheel content not verified"
            ),
            "repair": "Generate requirements-hashed.txt with pip-compile --generate-hashes",
        })

    # 3. pip version — is it pinned?
    pip_pin_match = re.search(r"pip==[^\s\\]+", content)
    factors.append({
        "factor": "pip_version",
        "value": pip_pin_match.group(0) if pip_pin_match else "NOT_PINNED",
        "deterministic": pip_pin_match is not None,
        "issue": None if pip_pin_match else (
            "pip version not pinned — inherits from base image, varies across rebuilds"
        ),
        "repair": "RUN pip install --upgrade pip==<version> before package install",
    })

    # 4. Build platform — declared?
    platform_match = re.search(r"--platform\s+(\S+)", content)
    factors.append({
        "factor": "build_platform",
        "value": platform_match.group(1) if platform_match else "UNDECLARED",
        "deterministic": platform_match is not None,
        "issue": None if platform_match else (
            "Build platform not declared — digest differs between linux/amd64 and linux/arm64"
        ),
        "repair": "Declare --platform=linux/amd64 in FROM or via docker build --platform",
    })

    # 5. Timestamps baked in?
    has_arg_build_date = "ARG BUILD_DATE" in content or "BUILD_DATE" in content
    factors.append({
        "factor": "embedded_timestamps",
        "value": "BUILD_DATE baked in" if has_arg_build_date else "No explicit timestamps",
        "deterministic": not has_arg_build_date,
        "issue": "BUILD_DATE ARG bakes timestamp into image" if has_arg_build_date else None,
        "repair": "Remove BUILD_DATE from image layers; use OCI label only if needed",
    })

    non_det = [f for f in factors if not f["deterministic"]]
    return {
        "dockerfile_path": str(dockerfile.relative_to(REPO_ROOT)).replace("\\", "/"),
        "total_factors_checked": len(factors),
        "non_deterministic_count": len(non_det),
        "factors": factors,
    }


def run_phase1() -> dict[str, Any]:
    print("[PHASE 1] Capturing static build identity baseline...")

    commit_sha = git_sha()
    dirty = git_dirty()
    branch = git_branch()
    dockerfile = RUNTIME_DIR / "Dockerfile"
    requirements = RUNTIME_DIR / "requirements.txt"

    manifest = capture_source_manifest()
    nondet = analyze_dockerfile_determinism(dockerfile)

    baseline = {
        "story_id": STORY_ID,
        "gap_id": GAP_ID,
        "captured_at": now_utc(),
        "phase": "static",
        "canonical_digest": CANONICAL_DIGEST,
        "source": {
            "repo": "Keyhole-Solution/keyhole-SDK",
            "branch": branch,
            "commit_sha": commit_sha,
            "dirty_worktree": dirty,
        },
        "build_inputs": {
            "dockerfile_sha256": sha256_file(dockerfile),
            "requirements_sha256": sha256_file(requirements),
            "requirements_content": requirements.read_text(encoding="utf-8").strip(),
            "base_image": re.search(r"^FROM\s+(\S+)", dockerfile.read_text(), re.MULTILINE).group(1),
        },
        "source_manifest": manifest,
        "non_determinism_analysis": nondet,
        "static_verdict": (
            "NON_DETERMINISTIC_INPUTS_IDENTIFIED"
            if nondet["non_deterministic_count"] > 0
            else "INPUTS_APPEAR_DETERMINISTIC_VERIFY_WITH_BUILD"
        ),
    }

    out_path = EVIDENCE_DIR / "build_identity_baseline.json"
    out_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"  Written: {out_path.relative_to(REPO_ROOT)}")

    nd_out = EVIDENCE_DIR / "static_nondet_analysis.json"
    nd_out.write_text(json.dumps(nondet, indent=2), encoding="utf-8")
    print(f"  Written: {nd_out.relative_to(REPO_ROOT)}")

    return baseline


# ---------------------------------------------------------------------------
# Phase 2: Docker build + digest comparison (requires Docker)
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    try:
        subprocess.check_output(["docker", "version"], stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def run_phase2(baseline: dict[str, Any]) -> dict[str, Any]:
    """
    Build from source and compare digest to canonical.
    Emits delta_report.json regardless of match outcome.
    """
    print("[PHASE 2] Running Docker build for digest comparison...")

    if not _docker_available():
        print("  SKIP: Docker not available in this environment.")
        print("  Run on a Linux CI host or pass RUN_DOCKER_BUILD=1 in an environment with Docker.")
        skip_report = {
            "story_id": STORY_ID,
            "gap_id": GAP_ID,
            "phase": "docker_build",
            "status": "SKIPPED",
            "reason": "Docker not available",
            "guidance": (
                "Run with RUN_DOCKER_BUILD=1 in a Docker-capable environment. "
                "The static non-determinism analysis in Phase 1 applies regardless."
            ),
        }
        out = EVIDENCE_DIR / "delta_report.json"
        out.write_text(json.dumps(skip_report, indent=2), encoding="utf-8")
        print(f"  Written: {out.relative_to(REPO_ROOT)}")
        return skip_report

    build_tag = "keyhole-cutover-c01-preflight:latest"
    print(f"  Building {build_tag} from {RUNTIME_DIR} (--no-cache)...")

    build_result = subprocess.run(
        ["docker", "build", "--no-cache", "--quiet", "-t", build_tag, str(RUNTIME_DIR)],
        capture_output=True,
        text=True,
    )

    if build_result.returncode != 0:
        error_report = {
            "story_id": STORY_ID,
            "gap_id": GAP_ID,
            "phase": "docker_build",
            "status": "BUILD_FAILED",
            "stderr": build_result.stderr[-3000:],
            "verdict": "BUILD_ERROR — cannot compare digest",
        }
        out = EVIDENCE_DIR / "delta_report.json"
        out.write_text(json.dumps(error_report, indent=2), encoding="utf-8")
        print(f"  BUILD FAILED — {out.relative_to(REPO_ROOT)}")
        return error_report

    # Inspect built image
    inspect_result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Id}}", build_tag],
        capture_output=True, text=True,
    )
    rebuilt_digest = inspect_result.stdout.strip()

    # Resolve the base image digest that was actually used
    base_image_ref = baseline["build_inputs"]["base_image"]
    pull_result = subprocess.run(
        ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", base_image_ref],
        capture_output=True, text=True,
    )
    resolved_base = pull_result.stdout.strip() or "UNKNOWN"

    # Pip version from built image
    pip_result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "pip", build_tag, "--version"],
        capture_output=True, text=True,
    )
    pip_version = pip_result.stdout.strip() or "UNKNOWN"

    # Platform
    platform_result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Os}}/{{.Architecture}}", build_tag],
        capture_output=True, text=True,
    )
    build_platform = platform_result.stdout.strip() or "UNKNOWN"

    canonical = baseline["canonical_digest"]
    match = rebuilt_digest.startswith(canonical) or canonical.startswith(rebuilt_digest)

    delta: dict[str, Any] = {
        "story_id": STORY_ID,
        "gap_id": GAP_ID,
        "phase": "docker_build",
        "measured_at": now_utc(),
        "canonical_digest": canonical,
        "rebuilt_digest": rebuilt_digest,
        "build_inputs_recorded": {
            "base_image_declared": base_image_ref,
            "base_image_resolved_digest": resolved_base,
            "pip_version": pip_version,
            "build_platform": build_platform,
        },
        "verdict": "REPRODUCIBLE" if match else "NON_DETERMINISTIC",
    }

    if not match:
        nd_factors = [
            f["factor"]
            for f in baseline["non_determinism_analysis"]["factors"]
            if not f["deterministic"]
        ]
        delta["non_deterministic_inputs"] = nd_factors
        delta["repair_candidates"] = [
            f["repair"]
            for f in baseline["non_determinism_analysis"]["factors"]
            if not f["deterministic"] and f.get("repair")
        ]
        delta["note"] = (
            "Digest mismatch is expected without base image digest pinning. "
            "See CUTOVER-C-02 and subsequent stories."
        )

    out = EVIDENCE_DIR / "delta_report.json"
    out.write_text(json.dumps(delta, indent=2), encoding="utf-8")
    print(f"  Verdict: {delta['verdict']}")
    print(f"  Written: {out.relative_to(REPO_ROOT)}")

    return delta


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"=== {STORY_ID} — Build Identity Baseline ===")
    print(f"Canonical digest: {CANONICAL_DIGEST}")
    print()

    baseline = run_phase1()
    print()
    print(f"Static verdict: {baseline['static_verdict']}")
    nd_count = baseline["non_determinism_analysis"]["non_deterministic_count"]
    if nd_count > 0:
        print(f"Non-deterministic inputs identified: {nd_count}")
        for f in baseline["non_determinism_analysis"]["factors"]:
            if not f["deterministic"]:
                print(f"  [{f['factor']}] {f['issue']}")
    print()

    run_docker = os.environ.get("RUN_DOCKER_BUILD", "").strip() not in ("", "0", "false", "no")
    if run_docker:
        delta = run_phase2(baseline)
        final_verdict = delta.get("verdict", "UNKNOWN")
    else:
        print("[PHASE 2] Skipped (set RUN_DOCKER_BUILD=1 to run with Docker).")
        final_verdict = "PENDING_DOCKER_BUILD"

    print()
    print("--- Summary ---")
    print(f"Story:            {STORY_ID}")
    print(f"Gap:              {GAP_ID}")
    print(f"Commit SHA:       {baseline['source']['commit_sha']}")
    print(f"Static verdict:   {baseline['static_verdict']}")
    print(f"Build verdict:    {final_verdict}")
    print(f"Evidence:         docs/evidence/cutover-c-01/")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
