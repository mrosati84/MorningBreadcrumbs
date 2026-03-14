"""
Middleware to serve user-uploaded media files in production.

WhiteNoise only serves static files (from STATIC_ROOT) and does not serve
MEDIA_ROOT, and it only indexes at startup so it's unsuitable for uploads.
This middleware serves files from MEDIA_ROOT when DEBUG is False so that
media URLs work without requiring a separate web server (e.g. Nginx).

Supports HTTP caching via Cache-Control, ETag, and Last-Modified so browsers
and reverse proxies can cache responses and conditional requests return 304.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseNotModified
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date, quote_etag


def _make_etag(st_mtime_ns: int, st_size: int) -> str:
    """Build a weak ETag from file mtime and size (no disk read of content)."""
    return quote_etag(f'"{st_mtime_ns:x}-{st_size:x}"')


class MediaMiddleware(MiddlewareMixin):
    """
    Serve files from MEDIA_ROOT at MEDIA_URL when DEBUG is False.
    Safe against path traversal by resolving paths and ensuring they stay under MEDIA_ROOT.
    Sets Cache-Control, ETag, and Last-Modified for HTTP caching and 304 responses.
    """

    def process_request(self, request):
        if settings.DEBUG:
            return None
        if request.method not in ("GET", "HEAD"):
            return None

        path = request.path.lstrip("/")
        media_url = (settings.MEDIA_URL or "").strip("/")
        if not media_url or not path.startswith(media_url + "/"):
            return None

        # Strip media URL prefix to get the relative path under MEDIA_ROOT
        rel_path = path[len(media_url) :].lstrip("/")
        if not rel_path:
            return None

        media_root = Path(settings.MEDIA_ROOT).resolve()
        # Resolve the requested path and ensure it stays under MEDIA_ROOT
        try:
            file_path = (media_root / rel_path).resolve()
        except (OSError, ValueError):
            return None
        if not file_path.is_relative_to(media_root) or ".." in rel_path:
            return None
        if not file_path.is_file():
            return None

        try:
            stat = file_path.stat()
        except OSError:
            return None

        etag = _make_etag(stat.st_mtime_ns, stat.st_size)
        last_modified = http_date(stat.st_mtime)

        # Conditional request: return 304 if the client has a valid cached copy
        if_none_match = request.META.get("HTTP_IF_NONE_MATCH", "").strip()
        if if_none_match and etag in (t.strip() for t in if_none_match.split(",")):
            return HttpResponseNotModified()
        if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE", "").strip()
        if if_modified_since and if_modified_since == last_modified:
            return HttpResponseNotModified()

        content_type, _ = mimetypes.guess_type(str(file_path))
        response = FileResponse(
            open(file_path, "rb"),
            content_type=content_type or "application/octet-stream",
            as_attachment=False,
        )
        response["Content-Length"] = stat.st_size
        response["ETag"] = etag
        response["Last-Modified"] = last_modified

        max_age = getattr(settings, "MEDIA_CACHE_MAX_AGE", 86400)  # default 1 day
        response["Cache-Control"] = f"public, max-age={max_age}"

        return response
