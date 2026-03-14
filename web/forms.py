from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from .models import Post

MAX_IMAGE_SIZE_BYTES = 1024 * 1024  # 1 MB
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = "__all__"

    def clean_featured_image(self) -> object:
        image = self.cleaned_data.get("featured_image")
        if not image:
            return image
        if image.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                "Image must be 1 MB or smaller. Current size: %(size)s MB.",
                code="file_too_large",
                params={"size": f"{image.size / (1024 * 1024):.2f}"},
            )
        content_type = getattr(image, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValidationError(
                "Only image files are allowed (JPEG, PNG, GIF, WebP).",
                code="invalid_image_type",
            )
        return image
