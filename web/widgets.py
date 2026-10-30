"""
Admin widget to pick the focal point of a Post's featured image.

The picker sits under the usual file input: clicking (or dragging on) the
image stores the point in the form's hidden `focal_x`/`focal_y` inputs, and
previews show how the front end will crop the image at each aspect ratio.
"""

from __future__ import annotations

from typing import override

from django.contrib.admin.widgets import AdminFileWidget
from django.db.models.fields.files import FieldFile

# Aspect ratios the front end crops featured images to (see .media--* in site.css).
PREVIEW_RATIOS: tuple[tuple[str, str], ...] = (
    ("Lead · desktop", "21 / 9"),
    ("News · desktop", "3 / 2"),
    ("Mobile", "4 / 5"),
)


class FocalPointImageInput(AdminFileWidget):
    template_name: str = "widgets/focal_point_image.html"

    def __init__(
        self,
        x_field: str = "focal_x",
        y_field: str = "focal_y",
        attrs: dict[str, object] | None = None,
    ) -> None:
        super().__init__(attrs)
        self.x_field: str = x_field
        self.y_field: str = y_field

    class Media:
        css: dict[str, tuple[str, ...]] = {"all": ("css/focal_point.css",)}
        js: tuple[str, ...] = ("js/focal_point.js",)

    @override
    def get_context(
        self, name: str, value: object, attrs: dict[str, object] | None
    ) -> dict[str, object]:
        context = super().get_context(name, value, attrs)
        image_url = ""
        if isinstance(value, FieldFile) and value.name:
            try:
                image_url = value.url
            except ValueError:
                image_url = ""
        context["focal"] = {
            "image_url": image_url,
            "x_field": self.x_field,
            "y_field": self.y_field,
            "ratios": PREVIEW_RATIOS,
        }
        return context
