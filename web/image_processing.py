"""
Optimize uploaded Post images: resize, convert to WebP, strip EXIF.

Uses Pillow (already required by Django ImageField). Runs on save so
images are stored optimized and served as-is with existing caching.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps


def _max_size() -> int:
    return getattr(settings, "POST_IMAGE_MAX_SIZE", 1200)


def _webp_quality() -> int:
    return getattr(settings, "POST_IMAGE_WEBP_QUALITY", 85)


def optimize_post_image(file_path: str | Path) -> str:
    """
    Optimize an image file in place or replace with a WebP version.

    - Resizes so the longest side is at most POST_IMAGE_MAX_SIZE (keeps aspect ratio).
    - Applies EXIF orientation then strips EXIF.
    - Saves as WebP with POST_IMAGE_WEBP_QUALITY.

    Returns the path to the (possibly new) image file. If the original was
    not WebP, the new file has the same stem with .webp and the original
    is removed.
    """
    path = Path(file_path)
    if not path.is_file():
        return str(path)

    with Image.open(path) as img:
        # Convert to RGB if necessary (e.g. PNG with transparency → RGB for WebP)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Apply EXIF orientation (e.g. rotate if camera was held sideways)
        img = ImageOps.exif_transpose(img)

        # Resize so longest side is at most POST_IMAGE_MAX_SIZE
        max_side = _max_size()
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

        # Save as WebP next to the original (same stem, .webp)
        base = path.parent / path.stem
        webp_path = base.with_suffix(".webp")

        # If already WebP, overwrite in place; otherwise write to new path
        save_path = path if path.suffix.lower() == ".webp" else webp_path
        img.save(save_path, "WEBP", quality=_webp_quality(), method=6)

        if save_path != path and path.exists():
            path.unlink()

        return str(save_path)
