#!/usr/bin/env python3
"""``{% scitex_project_picker %}``: the project picker an app places in its own UI.

    {% load scitex_project_picker %}
    {% scitex_project_picker scope="project" current=current_project %}

Renders nothing unless the app is project-scoped or explicitly opts into
``allow_user_scope=True``. The client additionally requires a provider with
``rememberScope``; the legacy HTTP provider never persists nullable user scope.
``current_scope="user"`` is explicit; an empty current project never means user.
``scope`` defaults to the
``app_scope`` context variable (scitex-app's context processor), else "user".
``provider_url`` defaults to the host's registered provider
(``settings.SCITEX_PROJECT_PROVIDER_URL``); ``current`` may be an id or a
project object the host provider maps with ``project_id``.
``navigate`` (default ``?project={id}``) is where a pick goes; pass "" to only
emit ``stx-project-selector:change`` for the app to handle.

``{% scitex_project_provider_meta %}`` is for the host's ``<head>``: it
advertises the provider to client-side pickers (``hostProjectProvider()``).
"""

from __future__ import annotations

from django import template
from django.template.loader import render_to_string
from django.utils.html import format_html

from scitex_sdk.ui.project_scope import (
    PROJECT_PROVIDER_META_NAME,
    host_project_provider_url,
    project_id_for,
)

register = template.Library()

SCOPE_USER = "user"
SCOPE_PROJECT = "project"
DEFAULT_NAVIGATE = "?project={id}"


def is_project_scope(scope) -> bool:
    """True for "project"; False for "user" or empty; raises on anything else."""
    normalized = str(scope or SCOPE_USER).strip().lower()
    if normalized not in (SCOPE_USER, SCOPE_PROJECT):
        raise ValueError(f"app scope must be 'user' or 'project', got {scope!r}")
    return normalized == SCOPE_PROJECT


def _signed_in(context) -> bool:
    request = context.get("request")
    user = getattr(request, "user", None)
    return request is None or bool(getattr(user, "is_authenticated", True))


@register.simple_tag(takes_context=True)
def scitex_project_picker(
    context,
    provider_url: str = "",
    scope=None,
    current="",
    navigate: str = DEFAULT_NAVIGATE,
    placeholder: str = "",
    allow_user_scope: bool = False,
    current_scope=None,
):
    if scope is None:
        scope = context.get("app_scope")
    project_scope = is_project_scope(scope)
    allow_user_scope = allow_user_scope is True
    if (not project_scope and not allow_user_scope) or not _signed_in(context):
        return ""
    if current_scope is not None:
        if current_scope not in (SCOPE_USER, SCOPE_PROJECT):
            raise ValueError("current scope must be explicit 'user' or 'project'")
    provider_url = provider_url or host_project_provider_url()
    if not provider_url:
        return ""
    return render_to_string(
        "scitex_sdk/ui/_project_picker.html",
        {
            "provider_url": provider_url,
            "current": project_id_for(current),
            "navigate": navigate,
            "placeholder": placeholder,
            "allow_user_scope": allow_user_scope,
            "current_scope": current_scope if allow_user_scope else None,
        },
    )


@register.simple_tag(takes_context=True)
def scitex_project_provider_meta(context):
    url = host_project_provider_url()
    if not url or context.get("request") is None or not _signed_in(context):
        return ""
    return format_html('<meta name="{}" content="{}">', PROJECT_PROVIDER_META_NAME, url)


# EOF
