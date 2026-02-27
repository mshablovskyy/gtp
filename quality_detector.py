"""
Image quality detector — flags junk photos for review.

Detects:
  - Blurry images (low Laplacian variance)
  - All black / very dark images
  - All white / overexposed images
  - Screenshots (specific aspect ratios + high edge density)
  - Corrupt / unreadable images
  - Tiny images (thumbnails, icons)
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageFilter

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic", ".heif"}


class IssueType(str, Enum):
    BLURRY = "Blurry"
    DARK = "Very dark / all black"
    OVEREXPOSED = "Overexposed / all white"
    SCREENSHOT = "Screenshot"
    CORRUPT = "Corrupt / unreadable"
    TINY = "Tiny image"


@dataclass
class QualityIssue:
    path: Path
    issue: IssueType
    detail: str  # e.g., "Laplacian variance: 12.3" or "Mean brightness: 5"
    score: float  # confidence 0-1 (higher = more likely junk)


ProgressCallback = Callable[[int, int, str], None]

# --- Detection thresholds ---
BLUR_THRESHOLD = 50.0        # Laplacian variance below this = blurry
DARK_MEAN_THRESHOLD = 15.0   # Mean brightness below this = too dark
DARK_STD_THRESHOLD = 10.0    # Std deviation below this (with low mean) = uniform black
BRIGHT_MEAN_THRESHOLD = 245.0  # Mean brightness above this = too bright
BRIGHT_STD_THRESHOLD = 10.0
TINY_MIN_PIXELS = 100 * 100  # Images smaller than 100x100 = tiny
SCREENSHOT_EDGE_RATIO = 0.15  # High edge pixel ratio suggests UI/text


# Common phone screenshot resolutions (width x height or height x width)
SCREENSHOT_RESOLUTIONS = {
    (1080, 1920), (1080, 2340), (1080, 2400), (1080, 2280),
    (1440, 2560), (1440, 3040), (1440, 3200),
    (750, 1334), (1125, 2436), (1170, 2532), (1179, 2556),
    (1284, 2778), (1290, 2796),
    (1242, 2208), (1242, 2688),
    (2048, 2732), (1668, 2388), (1620, 2160),  # tablets
}


def _is_screenshot_resolution(w: int, h: int) -> bool:
    return (w, h) in SCREENSHOT_RESOLUTIONS or (h, w) in SCREENSHOT_RESOLUTIONS


def _laplacian_variance(img: Image.Image) -> float:
    """Compute Laplacian variance as a measure of image sharpness."""
    gray = img.convert("L")
    # Resize for performance (sharpness detection doesn't need full res)
    if gray.width > 500 or gray.height > 500:
        gray.thumbnail((500, 500), Image.Resampling.LANCZOS)
    lap = gray.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1, offset=128,
    ))
    arr = np.array(lap, dtype=np.float64) - 128.0
    return float(np.var(arr))


def _analyze_image(path: Path) -> list[QualityIssue]:
    """Run all quality checks on a single image. Returns list of issues found."""
    issues = []

    try:
        img = Image.open(path)
        img.load()  # force decode to catch corrupt images
    except Exception as e:
        issues.append(QualityIssue(
            path=path, issue=IssueType.CORRUPT,
            detail=str(e), score=1.0,
        ))
        return issues

    w, h = img.size

    # Tiny image check
    if w * h < TINY_MIN_PIXELS:
        issues.append(QualityIssue(
            path=path, issue=IssueType.TINY,
            detail=f"{w}x{h} ({w * h} pixels)", score=0.9,
        ))
        return issues  # skip other checks for tiny images

    # Convert to grayscale array for brightness analysis
    gray = np.array(img.convert("L"), dtype=np.float64)
    mean_brightness = float(np.mean(gray))
    std_brightness = float(np.std(gray))

    # All black / very dark
    if mean_brightness < DARK_MEAN_THRESHOLD and std_brightness < DARK_STD_THRESHOLD:
        score = 1.0 - (mean_brightness / DARK_MEAN_THRESHOLD)
        issues.append(QualityIssue(
            path=path, issue=IssueType.DARK,
            detail=f"Mean brightness: {mean_brightness:.1f}, std: {std_brightness:.1f}",
            score=min(score, 1.0),
        ))

    # All white / overexposed
    if mean_brightness > BRIGHT_MEAN_THRESHOLD and std_brightness < BRIGHT_STD_THRESHOLD:
        score = (mean_brightness - BRIGHT_MEAN_THRESHOLD) / (255 - BRIGHT_MEAN_THRESHOLD)
        issues.append(QualityIssue(
            path=path, issue=IssueType.OVEREXPOSED,
            detail=f"Mean brightness: {mean_brightness:.1f}, std: {std_brightness:.1f}",
            score=min(score, 1.0),
        ))

    # Blurriness
    lap_var = _laplacian_variance(img)
    if lap_var < BLUR_THRESHOLD:
        score = 1.0 - (lap_var / BLUR_THRESHOLD)
        issues.append(QualityIssue(
            path=path, issue=IssueType.BLURRY,
            detail=f"Laplacian variance: {lap_var:.1f}",
            score=min(score, 1.0),
        ))

    # Screenshot detection
    if _is_screenshot_resolution(w, h):
        # Also check edge density — screenshots have lots of sharp UI edges
        if img.width > 500:
            thumb = img.copy()
            thumb.thumbnail((500, 500), Image.Resampling.LANCZOS)
        else:
            thumb = img
        edges = thumb.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges, dtype=np.float64)
        edge_ratio = float(np.sum(edge_arr > 50)) / edge_arr.size

        if edge_ratio > SCREENSHOT_EDGE_RATIO:
            issues.append(QualityIssue(
                path=path, issue=IssueType.SCREENSHOT,
                detail=f"Resolution: {w}x{h}, edge ratio: {edge_ratio:.2f}",
                score=0.8,
            ))

    return issues


def find_quality_issues(
    directory: str | Path,
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> list[QualityIssue]:
    """
    Scan directory for images with quality issues.

    Returns a list of QualityIssue, sorted by score (most likely junk first).
    """
    directory = Path(directory)

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

    _progress(0, len(image_files), "Analyzing image quality...")

    all_issues: list[QualityIssue] = []

    for i, fpath in enumerate(image_files):
        if _cancelled():
            return all_issues

        if i % 20 == 0 or i == len(image_files) - 1:
            _progress(i, len(image_files), f"Checking: {fpath.name}")

        issues = _analyze_image(fpath)
        all_issues.extend(issues)

    _progress(len(image_files), len(image_files),
              f"Found {len(all_issues)} issues in {len(image_files)} images")

    # Sort by score descending (most likely junk first)
    all_issues.sort(key=lambda x: x.score, reverse=True)

    return all_issues
