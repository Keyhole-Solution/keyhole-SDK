"""
Deterministic Docker build for services/test-runtime.

CE-V5-S51-CUTOVER-C-04 — Change A + Change B combined.

Approach:
  Creates an isolated temporary build context from the tracked files in
  services/test-runtime/, normalizes all file and directory modification
  times to SOURCE_DATE_EPOCH, then runs docker build from that context.
  The working tree is never mutated. The temp context is cleaned up on exit.

Change A (host mtime normalization):
  All file mtimes in the temp context are set to SOURCE_DATE_EPOCH before
  docker build is called. This makes COPY layer tars bit-identical across
  builds because the tar entry timestamps are derived from source file mtimes.

Change B (container-side epoch):
  The Dockerfile declares ARG SOURCE_DATE_EPOCH=0 / ENV SOURCE_DATE_EPOCH.
  This script passes --build-arg SOURCE_DATE_EPOCH=<epoch> so pip and other
  tools inside the container respect the epoch for their own output timestamps.

Usage:
    python scripts/build_deterministic.py [--tag TAG] [--dry-run]

Options:
    --tag TAG      Docker image tag (default: keyhole-test-runtime:deterministic)
    --dry-run      Print what would happen without building
    --epoch EPOCH  Override SOURCE_DATE_EPOCH (default: git commit timestamp)

Returns:
    0 on success, 1 on failure.
    Prints the built image digest on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_CONTEXT_SRC = REPO_ROOT / "services" / "test-runtime"


def get_commit_epoch() -> int:
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%ct"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
        return int(out.decode().strip())
    except Exception as e:
        raise RuntimeError(f"Cannot read git commit timestamp: {e}") from e


def get_tracked_files(src_dir: Path) -> list[str]:
    """Return paths of all git-tracked files, relative to src_dir."""
    out = subprocess.check_output(
        ["git", "ls-files"],
        cwd=src_dir,
        stderr=subprocess.DEVNULL,
    )
    return [p for p in out.decode().strip().split("\n") if p]


def build_normalized_context(src_dir: Path, dest_dir: Path, epoch: int) -> None:
    """
    Copy git-tracked files from src_dir into dest_dir.
    Set every file and directory mtime to epoch.
    The working tree in src_dir is never touched.
    """
    tracked = get_tracked_files(src_dir)
    for rel in tracked:
        src = src_dir / rel
        dst = dest_dir / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        os.utime(dst, (epoch, epoch))

    # Normalize directory mtimes bottom-up (children first)
    dirs = sorted(
        {f.parent for f in dest_dir.rglob("*") if f.is_file()},
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for d in dirs:
        os.utime(d, (epoch, epoch))
    os.utime(dest_dir, (epoch, epoch))


def run_docker_build(
    context_dir: Path,
    tag: str,
    epoch: int,
    dry_run: bool = False,
) -> dict:
    cmd = [
        "docker", "build",
        "--no-cache",
        "--build-arg", f"SOURCE_DATE_EPOCH={epoch}",
        "--quiet",
        "-t", tag,
        str(context_dir),
    ]

    if dry_run:
        print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
        return {"dry_run": True, "command": cmd}

    print(f"Building {tag} (SOURCE_DATE_EPOCH={epoch}) …")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # The --quiet flag prints only the image ID on stdout when successful.
    image_id = result.stdout.strip()

    if result.returncode != 0 and not image_id:
        raise RuntimeError(
            f"docker build failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )

    # Inspect the built image for layer hashes and platform
    inspect = subprocess.run(
        ["docker", "inspect", tag],
        capture_output=True, text=True,
    )
    img_data = json.loads(inspect.stdout)[0] if inspect.returncode == 0 else {}

    return {
        "tag": tag,
        "image_id": image_id or img_data.get("Id", ""),
        "created": img_data.get("Created", ""),
        "platform": f"{img_data.get('Os', '?')}/{img_data.get('Architecture', '?')}",
        "layers": img_data.get("RootFS", {}).get("Layers", []),
        "source_date_epoch": epoch,
        "source_date_epoch_utc": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", default="keyhole-test-runtime:deterministic")
    parser.add_argument("--epoch", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    epoch = args.epoch if args.epoch is not None else get_commit_epoch()
    print(f"SOURCE_DATE_EPOCH = {epoch}  ({datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()})")

    with tempfile.TemporaryDirectory(prefix="keyhole-build-ctx-") as tmp:
        tmp_path = Path(tmp)
        print(f"Building normalized context in {tmp_path} …")
        build_normalized_context(BUILD_CONTEXT_SRC, tmp_path, epoch)

        result = run_docker_build(tmp_path, args.tag, epoch, dry_run=args.dry_run)

    if args.dry_run:
        return 0

    print(f"\nImage ID : {result['image_id']}")
    print(f"Created  : {result['created']}")
    print(f"Platform : {result['platform']}")
    print(f"Layers   : {len(result.get('layers', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
