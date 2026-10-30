from django.db.models import QuerySet
from django.http import HttpRequest

from web.models import Issue


def issue_archive(_request: HttpRequest) -> dict[str, QuerySet[Issue]]:
    """Expose every issue to the shared "All issues" overlay (queried lazily)."""
    return {"issue_archive": Issue.objects.all()}
