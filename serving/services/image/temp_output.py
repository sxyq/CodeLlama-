"""Temporary image output with TTL cleanup (no long-term gallery).

All service outputs (text-to-image and image-to-image) are written under
TEMP_OUTPUT_ROOT. A daemon thread removes files older than
IMAGE_OUTPUT_RETENTION_SECONDS every IMAGE_CLEANUP_INTERVAL_SECONDS, and
runs one sweep immediately at startup.

Delete safety: only regular files whose *resolved* parent is exactly
TEMP_OUTPUT_ROOT are removed. Symlinks are never followed (a symlink is
skipped entirely, and a path whose resolve() escapes the root is skipped),
so the cleaner cannot delete anything outside the temp directory — never
models, logs, source, config, or upload originals elsewhere.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

TEMP_OUTPUT_ROOT = Path(os.environ.get(
    "IMAGE_OUTPUT_DIR", "/home/syy/ai-serving/tmp/image-output"
))
RETENTION_SECONDS = int(os.environ.get("IMAGE_OUTPUT_RETENTION_SECONDS", "1800"))
CLEANUP_INTERVAL_SECONDS = int(os.environ.get("IMAGE_CLEANUP_INTERVAL_SECONDS", "300"))


def write_output(name: str, blob: bytes) -> Path:
    """Write one output file under TEMP_OUTPUT_ROOT and return its path."""
    TEMP_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEMP_OUTPUT_ROOT / name
    path.write_bytes(blob)
    return path


def _is_inside_root(path: Path) -> bool:
    """True only when the resolved path is a direct child of the resolved root."""
    try:
        resolved = path.resolve(strict=False)
        root = TEMP_OUTPUT_ROOT.resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    return resolved.parent == root


def cleanup_once(now: float | None = None) -> int:
    """Delete expired regular files directly inside TEMP_OUTPUT_ROOT.

    Returns the number of files removed. Symlinks are skipped without
    following them; anything whose resolved location is outside the root
    is refused.
    """
    if not TEMP_OUTPUT_ROOT.is_dir():
        return 0
    now = time.time() if now is None else now
    removed = 0
    try:
        entries = list(os.scandir(TEMP_OUTPUT_ROOT))
    except OSError:
        return 0
    for entry in entries:
        try:
            if entry.is_symlink():
                continue  # never follow, never delete the target
            if not entry.is_file(follow_symlinks=False):
                continue  # directories / special files untouched
            age = now - entry.stat(follow_symlinks=False).st_mtime
            if age < RETENTION_SECONDS:
                continue
            candidate = Path(entry.path)
            if not _is_inside_root(candidate):
                continue  # escaped (weird mount/symlink) -> refuse
            os.unlink(candidate)
            removed += 1
        except OSError:
            continue
    return removed


def _cleanup_loop() -> None:
    while True:
        try:
            cleanup_once()
        except Exception:
            pass  # cleaner must never die; next sweep retries
        time.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cleaner() -> threading.Thread:
    """Startup sweep + periodic sweep; returns the daemon thread."""
    thread = threading.Thread(target=_cleanup_loop, name="image-ttl-cleaner", daemon=True)
    thread.start()
    return thread
