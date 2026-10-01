#!/usr/bin/env python3
"""``{% stx_help "app" %}``: in-app "How to use" panel + first-open tour.

    {% load stx_help %}
    {% stx_help "scholar" %}

Renders the `?` button and the guide's JSON payload (as a json_script element
the component reads on load). The leaf app declares its steps in a small
JSON/YAML file and embeds it with this tag — no component code. EN/JA via the
per-language ``title``/``body`` shape; the active language comes from the
document's ``<html lang>`` (host active language), same as the rest of the
shared shell.

The wrapper loads ``css/app/app-help.css`` and ``js/app/app-help.js``; the
script mounts every ``[data-stx-help]`` root and exposes ``window.stxHelp``.
"""

from __future__ import annotations

import json
import re

from django import template
from django.utils.html import format_html

from .scitex_static import versioned_static

register = template.Library()


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value)


@register.simple_tag
def stx_help(app: str, steps_json: str = ""):
    """Render the help button + guide payload for `app`.

    Parameters
    ----------
    app:
        The app identifier (storage namespace + script element id).
    steps_json:
        A JSON string of the steps list, e.g.
        ``'[{"title": "Open a project", "body": "Pick one from the header."}]'``.
        When empty, the component still mounts (the `?` button renders) and
        reads the guide from a ``<script id="stx-app-help-<app>">`` element
        the app may emit separately.
    """
    steps = []
    if steps_json:
        try:
            steps = json.loads(steps_json)
        except (json.JSONDecodeError, TypeError):
            steps = []
    guide = {"app": app, "steps": steps}
    payload = json.dumps(guide, separators=(",", ":"))
    script_id = f"stx-app-help-{_slug(app)}"
    return format_html(
        '<link rel="stylesheet" href="{}">\n'
        '<div class="stx-app-help" data-stx-help="{}"></div>\n'
        '<script type="application/json" id="{}">{}</script>\n'
        '<script type="module" src="{}"></script>',
        versioned_static("scitex_sdk/ui/css/app/app-help.css"),
        app,
        script_id,
        payload,
        versioned_static("scitex_sdk/ui/js/app/app-help.js"),
    )


# EOF
