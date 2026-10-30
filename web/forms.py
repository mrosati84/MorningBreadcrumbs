from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import Post

MAX_IMAGE_SIZE_BYTES = 1024 * 1024  # 1 MB
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


if TYPE_CHECKING:
    PostAdminFormBase = forms.ModelForm[Post]
else:
    PostAdminFormBase = forms.ModelForm


class PostAdminForm(PostAdminFormBase):
    class Meta:
        model: type[Post] = Post
        fields: str = "__all__"

    def clean_featured_image(self) -> object:
        image: object = self.cleaned_data.get("featured_image")
        # Only a new upload needs checking: an image already stored passed
        # this validation when it was uploaded (and None/False mean "no image").
        if not isinstance(image, UploadedFile):
            return image
        if image.size is not None and image.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                "Image must be 1 MB or smaller. Current size: %(size)s MB.",
                code="file_too_large",
                params={"size": f"{image.size / (1024 * 1024):.2f}"},
            )
        content_type = image.content_type or ""
        if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValidationError(
                "Only image files are allowed (JPEG, PNG, GIF, WebP).",
                code="invalid_image_type",
            )
        return image
