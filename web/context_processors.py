from django.db.models import QuerySet
from django.http import HttpRequest

from web.models import Issue, Post


def issue_archive(_request: HttpRequest) -> dict[str, QuerySet[Issue] | QuerySet[Post]]:
    """Expose every issue and post to the shared "All issues" overlay (queried lazily)."""
    return {"issue_archive": Issue.objects.all(), "all_posts": Post.objects.all()}
