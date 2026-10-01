#!/usr/bin/env python3
"""``{% app_static %}``: a static URL that changes whenever the file does.

    {% load scitex_static %}
    <script src="{% app_static 'stats/js/app.js' %}"></script>
    -> /static/stats/js/app.js?v=3f9a1c2e4b7d

Plain ``{% static %}`` URLs never change, so a phone keeps a stale app.js
after a deploy. The version is a short content hash, recomputed only when the
file's mtime or size changes, so an edit busts caches without a version bump.
"""

from __future__ import annotations

import hashlib
import os

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

register = template.Library()

_HASH_LENGTH = 12
_locations: dict[str, str] = {}
_hashes: dict[str, tuple[int, int, str]] = {}


def _locate(path: str) -> str | None:
    if path in _locations:
        return _locations[path]
    found = finders.find(path)
    if not isinstance(found, str):
        try:
            found = staticfiles_storage.path(path)
        except Exception:  # remote storage or no STATIC_ROOT: no local file to hash
            found = None
    if found and os.path.isfile(found):
        _locations[path] = found
        return found
    return None


def asset_version(path: str) -> str:
    """Short content hash of a static file, or ``""`` when it is not found."""
    location = _locate(path)
    if not location:
        return ""
    version = file_version(location)
    if not version:
        _locations.pop(path, None)
    return version


def file_version(location: str) -> str:
    """Short content hash of a file on disk, cached until mtime or size change."""
    try:
        stat = os.stat(location)
    except OSError:
        return ""
    cached = _hashes.get(location)
    if cached and cached[:2] == (stat.st_mtime_ns, stat.st_size):
        return cached[2]
    digest = hashlib.sha256()
    with open(location, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    version = digest.hexdigest()[:_HASH_LENGTH]
    _hashes[location] = (stat.st_mtime_ns, stat.st_size, version)
    return version


def versioned_static(path: str) -> str:
    """``static(path)`` plus ``?v=<content hash>`` when the file is found."""
    url = static(path)
    version = asset_version(path)
    if not version:
        return url
    return f"{url}{'&' if '?' in url else '?'}v={version}"


@register.simple_tag
def app_static(path: str) -> str:
    return versioned_static(path)


# EOF
