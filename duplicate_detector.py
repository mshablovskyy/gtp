"""
SHA-256 exact duplicate detection.

Two-pass approach:
  Pass 1: Group files by size (fast, eliminates most files)
  Pass 2: Hash only same-size candidates with SHA-256
"""

import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class DuplicateGroup:
    sha256: str
    file_size: int
    paths: list[Path] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str], None]  # (current, total, message)


def _sha256_file(path: Path, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_exact_duplicates(
    directory: str | Path,
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> list[DuplicateGroup]:
    """
    Scan a directory for byte-identical duplicate files.

    Returns a list of DuplicateGroup, each containing 2+ identical files.
    """
    directory = Path(directory)

    def _cancelled():
        return cancel_flag() if cancel_flag else False

    def _progress(current, total, msg=""):
        if on_progress:
            on_progress(current, total, msg)

    # Pass 1: Group by file size
    _progress(0, 0, "Scanning file sizes...")
    size_groups: dict[int, list[Path]] = defaultdict(list)

    all_files = []
    for root, _, filenames in os.walk(directory):
        for name in filenames:
            all_files.append(Path(root) / name)

    for i, fpath in enumerate(all_files):
        if _cancelled():
            return []
        try:
            size = fpath.stat().st_size
            if size > 0:  # skip empty files
                size_groups[size].append(fpath)
        except OSError:
            continue

    # Filter to only sizes with 2+ files
    candidates = []
    for size, paths in size_groups.items():
        if len(paths) >= 2:
            candidates.extend(paths)

    _progress(0, len(candidates), f"Hashing {len(candidates)} candidate files...")

    # Pass 2: SHA-256 hash candidates
    hash_groups: dict[tuple[int, str], list[Path]] = defaultdict(list)

    for i, fpath in enumerate(candidates):
        if _cancelled():
            return []
        _progress(i, len(candidates), f"Hashing: {fpath.name}")
        try:
            digest = _sha256_file(fpath)
            size = fpath.stat().st_size
            hash_groups[(size, digest)].append(fpath)
        except OSError:
            continue

    _progress(len(candidates), len(candidates), "Hashing complete")

    # Build result — only groups with 2+ files
    results = []
    for (size, digest), paths in hash_groups.items():
        if len(paths) >= 2:
            results.append(DuplicateGroup(sha256=digest, file_size=size, paths=paths))

    # Sort by reclaimable space (largest groups first)
    results.sort(key=lambda g: g.file_size * (len(g.paths) - 1), reverse=True)

    return results
