from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from django.db import connection
from django.db.models import Max, Q, QuerySet, Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from web.models import Category, Issue, Post

CATEGORY_PARAM = "c"


@dataclass(frozen=True)
class Tab:
    """One entry of the category bar: a filter link with its post count."""

    label: str
    count: int
    url: str
    active: bool


@dataclass(frozen=True)
class Section:
    """The posts of one category inside an issue."""

    category: Category
    posts: list[Post]

    @property
    def lead(self) -> Post:
        return self.posts[0]

    @property
    def rest(self) -> list[Post]:
        return self.posts[1:]


def _category_order(category: Category) -> tuple[bool, str]:
    # News always comes first, the rest alphabetically.
    return (not category.is_news, str(category.name).lower())


def _with_params(base_url: str, **params: str) -> str:
    query = urlencode({key: value for key, value in params.items() if value})
    return f"{base_url}?{query}" if query else base_url


def _category_tabs(
    request: HttpRequest, posts: list[Post], base_url: str, **params: str
) -> tuple[list[Tab], Category | None]:
    """
    Build the category bar for `posts` and resolve the selected category.

    Only categories that actually have posts get a tab. An unknown category
    slug in the query string is a 404 rather than a silently empty page.
    """
    counts = Counter(post.category.id for post in posts)
    categories = sorted(
        {post.category.id: post.category for post in posts}.values(),
        key=_category_order,
    )

    slug = request.GET.get(CATEGORY_PARAM, "")
    selected = None
    if slug:
        selected = next((c for c in categories if c.slug == slug), None)
        if selected is None:
            raise Http404("No such category in this listing.")

    tabs = [
        Tab(
            label="All",
            count=len(posts),
            url=_with_params(base_url, **params),
            active=selected is None,
        )
    ]
    tabs += [
        Tab(
            label=str(category.name),
            count=counts[category.id],
            url=_with_params(base_url, **params, **{CATEGORY_PARAM: category.slug}),
            active=category == selected,
        )
        for category in categories
    ]
    return tabs, selected


def _sections(posts: list[Post]) -> list[Section]:
    grouped: dict[int, list[Post]] = {}
    for post in posts:
        grouped.setdefault(post.category.id, []).append(post)
    sections = [
        Section(category=group[0].category, posts=group) for group in grouped.values()
    ]
    return sorted(sections, key=lambda section: _category_order(section.category))


def _latest_update(posts: list[Post]) -> datetime | None:
    return max((post.created_at for post in posts), default=None)


def _issue_posts(issue: Issue) -> QuerySet[Post]:
    return (
        Post.objects.filter(issue=issue)
        .select_related("category")
        .order_by("-created_at")
    )


def _active_issue() -> Issue | None:
    return Issue.objects.filter(is_active=True).first()


def _render_issue(request: HttpRequest, issue: Issue | None) -> HttpResponse:
    posts = list(_issue_posts(issue)) if issue else []
    base_url = issue.get_absolute_url() if issue else reverse("web:home")
    tabs, selected = _category_tabs(request, posts, base_url)
    visible = [post for post in posts if selected is None or post.category == selected]

    return render(
        request,
        "home.html",
        {
            "issue": issue,
            "updated_at": _latest_update(posts),
            "entry_count": len(posts),
            "tabs": tabs,
            "selected_category": selected,
            "sections": _sections(visible),
            "clear_url": base_url,
        },
    )


def home(request: HttpRequest) -> HttpResponse:
    """The active issue, grouped by category."""
    return _render_issue(request, _active_issue())


def issue_detail(request: HttpRequest, number: int) -> HttpResponse:
    """An archived issue. The active one is only served from the home page."""
    issue = get_object_or_404(Issue, number=number)
    if issue.is_active:
        return redirect(_with_params(reverse("web:home"), **request.GET.dict()))
    return _render_issue(request, issue)


def _search_posts(query: str) -> list[Post]:
    """Search posts of every issue by title and description."""
    posts = Post.objects.select_related("category", "issue")
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import TrigramSimilarity

        # Combined similarity on title and description; threshold allows typo tolerance
        similarity = Coalesce(TrigramSimilarity("title", query), Value(0.0)) + Coalesce(
            TrigramSimilarity("description", query), Value(0.0)
        )
        posts = (
            posts.annotate(similarity=similarity)
            .filter(similarity__gt=0.1)
            .order_by("-similarity", "-created_at")
        )
    else:
        # Fallback for SQLite etc.: plain substring match
        posts = posts.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).order_by("-created_at")
    return list(posts)


def search(request: HttpRequest) -> HttpResponse:
    query = (request.GET.get("q") or "").strip()
    if not query:
        return redirect("web:home")

    hits = _search_posts(query)
    tabs, selected = _category_tabs(request, hits, reverse("web:search"), q=query)
    results = [post for post in hits if selected is None or post.category == selected]

    # The header always refers to the active issue, wherever the results come from.
    active = _active_issue()
    updated_at = (
        Post.objects.filter(issue=active).aggregate(latest=Max("created_at"))["latest"]
        if active
        else None
    )

    return render(
        request,
        "search_results.html",
        {
            "query": query,
            "issue": active,
            "updated_at": updated_at,
            "tabs": tabs,
            "selected_category": selected,
            "results": results,
            "clear_url": reverse("web:home"),
        },
    )
