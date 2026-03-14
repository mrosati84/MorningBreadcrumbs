"""
Signal handlers for the web app.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.files.base import File
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image_processing import optimize_post_image
from .models import Post


@receiver(post_save, sender=Post)
def optimize_post_featured_image(sender: type[Post], instance: Post, **kwargs: object) -> None:
    """
    After a Post is saved, optimize its featured_image if present.

    Converts to WebP, resizes, and strips EXIF. If the file is replaced
    by a .webp, the model is updated so the field points to the new path.
    """
    if not instance.featured_image:
        return

    try:
        old_path = instance.featured_image.path
    except (ValueError, OSError):
        return

    if not os.path.isfile(old_path):
        return

    new_path = optimize_post_image(old_path)
    if new_path == old_path:
        return

    # Update the field to point to the new file (same dir, new extension)
    new_name = os.path.relpath(new_path, settings.MEDIA_ROOT)
    with open(new_path, "rb") as f:
        instance.featured_image.save(os.path.basename(new_path), File(f), save=False)
    instance.save(update_fields=["featured_image"])
