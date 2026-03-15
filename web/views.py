from collections import defaultdict

from django.conf import settings
from django.db import connection
from django.db.models import Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.views import LoginView as AuthLoginView

from web.models import Category, Post


class LoginView(AuthLoginView):
    """Login view that redirects authenticated users to the home page."""

    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)


def home(request):
    categories = list(Category.objects.order_by("name"))
    if not categories:
        return render(request, "home.html", {"categories": []})

    category_ids = [c.id for c in categories]
    posts_by_category = defaultdict(list)
    for post in Post.objects.filter(category_id__in=category_ids).order_by(
        "-created_at"
    ).select_related("category"):
        if len(posts_by_category[post.category_id]) < 3:
            posts_by_category[post.category_id].append(post)

    for cat in categories:
        cat.recent_posts = posts_by_category.get(cat.id, [])

    return render(request, "home.html", {"categories": categories})


def category_detail(request, slug):
    """Category detail page: all posts in the category, 3-column grid."""
    category = get_object_or_404(Category, slug=slug)
    posts = list(
        Post.objects.filter(category=category)
        .order_by("-created_at")
        .select_related("category")
    )
    return render(
        request,
        "category_detail.html",
        {
            "category": category,
            "posts": posts,
            "active_category_slug": category.slug,
        },
    )


def search(request):
    """Search posts by title and description with typo tolerance (PostgreSQL trigram)."""
    query = (request.GET.get("q") or "").strip()
    posts = []
    if query:
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import TrigramSimilarity

            # Combined similarity on title and description; threshold allows typo tolerance
            similarity = Coalesce(
                TrigramSimilarity("title", query), Value(0.0)
            ) + Coalesce(TrigramSimilarity("description", query), Value(0.0))
            posts = list(
                Post.objects.annotate(similarity=similarity)
                .filter(similarity__gt=0.1)
                .order_by("-similarity", "-created_at")
                .select_related("category")
            )
        else:
            # Fallback for SQLite etc.: plain substring match
            posts = list(
                Post.objects.filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )
                .order_by("-created_at")
                .select_related("category")
            )
    return render(
        request,
        "search_results.html",
        {"query": query, "posts": posts},
    )
