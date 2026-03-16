from __future__ import annotations

from typing import TYPE_CHECKING, final

from django.contrib import admin

from .forms import PostAdminForm
from .models import Category, Post, Tag

if TYPE_CHECKING:
    CategoryAdminBase = admin.ModelAdmin[Category]
    TagAdminBase = admin.ModelAdmin[Tag]
    PostAdminBase = admin.ModelAdmin[Post]
else:
    CategoryAdminBase = admin.ModelAdmin
    TagAdminBase = admin.ModelAdmin
    PostAdminBase = admin.ModelAdmin


@final
@admin.register(Category)
class CategoryAdmin(CategoryAdminBase):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@final
@admin.register(Tag)
class TagAdmin(TagAdminBase):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@final
@admin.register(Post)
class PostAdmin(PostAdminBase):
    form = PostAdminForm
    list_display = ("title", "category", "tags_list", "link")
    list_filter = ("category", "tags")
    search_fields = ("title", "description", "link")
    autocomplete_fields = ("category", "tags")
    filter_horizontal = ("tags",)
    ordering = ("title",)

    @admin.display(description="Tags")
    def tags_list(self, obj: Post) -> str:
        return ", ".join(tag.name for tag in obj.tags.all())


admin.site.site_header = "Morning Breadcrumbs"
admin.site.site_title = "Morning Breadcrumbs"
admin.site.index_title = "Morning Breadcrumbs"
