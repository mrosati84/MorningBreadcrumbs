"""
Signal handlers for the web app.
"""

from __future__ import annotations

import os
from typing import cast

from django.db.models.fields.files import ImageFieldFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image_processing import optimize_post_image
from .models import Post


@receiver(post_save, sender=Post)
def optimize_post_featured_image(instance: Post, **_kwargs: object) -> None:
    """
    After a Post is saved, optimize its featured_image if present.

    Converts to WebP, resizes, and strips EXIF. If the file is replaced
    by a .webp, the model is updated so the field points to the new path.
    """
    image = cast(ImageFieldFile | None, instance.featured_image)
    if not image or not image.name:
        return

    try:
        old_path = image.path
    except (ValueError, OSError):
        return

    if not os.path.isfile(old_path):
        return

    new_path = optimize_post_image(old_path)
    if new_path == old_path:
        return

    # The optimized file already sits next to the original: just point the
    # field at it (same directory, new extension) instead of re-uploading it.
    image.name = os.path.join(os.path.dirname(image.name), os.path.basename(new_path))
    instance.save(update_fields=["featured_image"])
