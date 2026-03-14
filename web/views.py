from collections import defaultdict

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
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
    """Placeholder: category detail page (skip implementation)."""
    raise Http404("Category detail not implemented yet.")
