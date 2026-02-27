"""
Perceptual hash similar photo detection.

Uses imagehash (pHash by default) to find visually similar images.
Groups results with Union-Find for disjoint sets.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import imagehash
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic", ".heif"}

HASH_FUNCTIONS = {
    "phash": imagehash.phash,
    "dhash": imagehash.dhash,
    "average_hash": imagehash.average_hash,
    "whash": imagehash.whash,
}


@dataclass
class SimilarMember:
    path: Path
    distance: int


@dataclass
class SimilarGroup:
    reference: Path
    members: list[SimilarMember] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str], None]


class UnionFind:
    def __init__(self):
        self.parent: dict[int, int] = {}
        self.rank: dict[int, int] = {}

    def find(self, x: int) -> int:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def find_similar_photos(
    directory: str | Path,
    threshold: int = 8,
    hash_func: str = "phash",
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> list[SimilarGroup]:
    """
    Scan directory for visually similar images.

    Args:
        directory: Folder to scan
        threshold: Hamming distance threshold (0=identical, higher=more lenient)
        hash_func: Hash algorithm ("phash", "dhash", "average_hash", "whash")
        on_progress: Callback (current, total, message)
        cancel_flag: Callable returning True to abort

    Returns:
        List of SimilarGroup, each with a reference image and similar members.
    """
    directory = Path(directory)
    hasher = HASH_FUNCTIONS.get(hash_func, imagehash.phash)

    def _cancelled():
        return cancel_flag() if cancel_flag else False

    def _progress(current, total, msg=""):
        if on_progress:
            on_progress(current, total, msg)

    # Collect image files
    image_files: list[Path] = []
    for root, _, filenames in os.walk(directory):
        for name in filenames:
            if Path(name).suffix.lower() in IMAGE_EXTENSIONS:
                image_files.append(Path(root) / name)

    if not image_files:
        return []

    # Phase 1: Compute hashes
    _progress(0, len(image_files), "Computing perceptual hashes...")
    hashes: list[tuple[Path, imagehash.ImageHash]] = []

    for i, fpath in enumerate(image_files):
        if _cancelled():
            return []
        _progress(i, len(image_files), f"Hashing: {fpath.name}")
        try:
            img = Image.open(fpath)
            h = hasher(img)
            hashes.append((fpath, h))
        except Exception:
            continue  # skip corrupt/unreadable images

    _progress(len(image_files), len(image_files), f"Hashed {len(hashes)} images")

    if len(hashes) < 2:
        return []

    # Phase 2: Compare pairs and group with Union-Find
    _progress(0, 0, "Comparing images...")
    uf = UnionFind()
    n = len(hashes)
    # Store pairwise distances for members that are similar
    distances: dict[tuple[int, int], int] = {}

    total_pairs = n * (n - 1) // 2
    pair_count = 0

    for i in range(n):
        if _cancelled():
            return []
        for j in range(i + 1, n):
            dist = hashes[i][1] - hashes[j][1]  # Hamming distance
            if dist <= threshold:
                uf.union(i, j)
                distances[(i, j)] = dist
                distances[(j, i)] = dist
            pair_count += 1

        # Report progress every 100 images
        if i % 100 == 0:
            _progress(pair_count, total_pairs, f"Comparing... ({pair_count}/{total_pairs} pairs)")

    _progress(total_pairs, total_pairs, "Comparison complete")

    # Phase 3: Build groups from Union-Find
    groups_dict: dict[int, list[int]] = {}
    for i in range(n):
        root = uf.find(i)
        if root not in groups_dict:
            groups_dict[root] = []
        groups_dict[root].append(i)

    # Filter to groups with 2+ members
    results = []
    for root_idx, members in groups_dict.items():
        if len(members) < 2:
            continue

        ref_idx = members[0]
        ref_path = hashes[ref_idx][0]
        group = SimilarGroup(reference=ref_path)

        for idx in members:
            dist = distances.get((ref_idx, idx), 0)
            group.members.append(SimilarMember(path=hashes[idx][0], distance=dist))

        # Sort members by distance from reference
        group.members.sort(key=lambda m: m.distance)
        results.append(group)

    # Sort groups by size (largest first)
    results.sort(key=lambda g: len(g.members), reverse=True)

    return results
