"""
Middleware to serve user-uploaded media files in production.

WhiteNoise only serves static files (from STATIC_ROOT) and does not serve
MEDIA_ROOT, and it only indexes at startup so it's unsuitable for uploads.
This middleware serves files from MEDIA_ROOT when DEBUG is False so that
media URLs work without requiring a separate web server (e.g. Nginx).
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.utils.deprecation import MiddlewareMixin


class MediaMiddleware(MiddlewareMixin):
    """
    Serve files from MEDIA_ROOT at MEDIA_URL when DEBUG is False.
    Safe against path traversal by resolving paths and ensuring they stay under MEDIA_ROOT.
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

        content_type, _ = mimetypes.guess_type(str(file_path))
        response = FileResponse(
            open(file_path, "rb"),
            content_type=content_type or "application/octet-stream",
            as_attachment=False,
        )
        response["Content-Length"] = file_path.stat().st_size
        return response
