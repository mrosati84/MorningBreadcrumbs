from __future__ import annotations

from typing import TYPE_CHECKING, final, override

from django.contrib import admin, messages
from django.db.models import Count, Max, QuerySet
from django.http import HttpRequest
from django.utils import timezone

from .forms import PostAdminForm
from .models import Category, Issue, Post, Tag

if TYPE_CHECKING:
    CategoryAdminBase = admin.ModelAdmin[Category]
    TagAdminBase = admin.ModelAdmin[Tag]
    IssueAdminBase = admin.ModelAdmin[Issue]
    PostAdminBase = admin.ModelAdmin[Post]
else:
    CategoryAdminBase = admin.ModelAdmin
    TagAdminBase = admin.ModelAdmin
    IssueAdminBase = admin.ModelAdmin
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
@admin.register(Issue)
class IssueAdmin(IssueAdminBase):
    list_display = ("__str__", "published_on", "subject", "is_active", "post_count")
    list_display_links = ("__str__",)
    list_filter = ("is_active",)
    search_fields = ("number", "subject")
    ordering = ("-number",)
    actions = ("make_active",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[Issue]:
        return super().get_queryset(request).annotate(post_count=Count("posts"))

    @override
    def get_changeform_initial_data(
        self, request: HttpRequest
    ) -> dict[str, str | list[str]]:
        last_number: int = Issue.objects.aggregate(last=Max("number"))["last"] or 0
        defaults: dict[str, str | list[str]] = {
            "number": str(last_number + 1),
            "published_on": timezone.localdate().isoformat(),
        }
        # Values passed in the query string win over the defaults.
        return defaults | super().get_changeform_initial_data(request)

    @admin.display(description="Posts", ordering="post_count")
    def post_count(self, obj: Issue) -> int:
        return getattr(obj, "post_count", 0)

    @admin.action(description="Set as the active issue")
    def make_active(self, request: HttpRequest, queryset: QuerySet[Issue]) -> None:
        if queryset.count() != 1:
            self.message_user(
                request, "Select exactly one issue to activate.", messages.ERROR
            )
            return
        issue = queryset.get()
        issue.activate()
        self.message_user(request, f"Issue {issue} is now active.", messages.SUCCESS)


@final
@admin.register(Post)
class PostAdmin(PostAdminBase):
    form = PostAdminForm
    list_display = ("title", "issue", "category", "tags_list", "link")
    list_filter = ("issue", "category", "tags")
    search_fields = ("title", "description", "link")
    autocomplete_fields = ("issue", "category", "tags")
    filter_horizontal = ("tags",)
    ordering = ("title",)

    @override
    def get_changeform_initial_data(
        self, request: HttpRequest
    ) -> dict[str, str | list[str]]:
        initial = super().get_changeform_initial_data(request)
        active = Issue.objects.filter(is_active=True).first()
        if active is None:
            return initial
        # New posts go to the active issue unless the query string says otherwise.
        return {"issue": str(active.id)} | initial

    @admin.display(description="Tags")
    def tags_list(self, obj: Post) -> str:
        return ", ".join(tag.name for tag in obj.tags.all())


admin.site.site_header = "Morning Breadcrumbs"
admin.site.site_title = "Morning Breadcrumbs"
admin.site.index_title = "Morning Breadcrumbs"
