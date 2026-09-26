#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the SciTeX App Creator wizard.

``index`` is the server-rendered wizard (starter cards + forms); every
mutation is a JSON API wired to the appmaker ENGINE in scitex-app
(``scitex_app.appmaker`` — the implementation consolidates into the SDK
gradually, per the facade pattern):

- ``api/validate-input`` — wizard field validation, no filesystem touch.
- ``api/create`` — scaffold via ``init_app`` into a fresh directory.
- ``api/validate-app`` — ``validate_with_warnings`` on an app dir.
- ``api/publish`` / ``api/dev-install`` — the engine's cloud hooks.

Error contract: bad input is 400 JSON ``{"errors": [...]}``; engine
results (including engine-level failure such as failed local
validation) are 200 JSON carrying the engine's own ``success`` flag —
a completed validation is not a malformed request. Unexpected
exceptions are 500 JSON, never an HTML traceback page.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from . import (
    DEFAULT_STARTER,
    STARTERS,
    STARTERS_BY_KEY,
    app_module_name,
    starter_brief_section,
    target_slug,
    validate_create_input,
)


def _starter_payload():
    return [
        {
            "key": s.key,
            "label": s.label,
            "hint": s.hint,
            "icon": s.icon,
            "creates": s.creates,
            "builds_first": s.builds_first,
        }
        for s in STARTERS
    ]


def index(request):
    """The wizard page: starter cards, create form, validate/publish tools."""
    return render(
        request,
        "scitex_sdk_creator/wizard.html",
        {"starters": _starter_payload(), "default_starter": DEFAULT_STARTER},
    )


@require_GET
def healthz(request):
    """Liveness probe for the launcher and the host's health checks."""
    return JsonResponse({"ok": True, "app": "scitex-sdk-creator"})


@require_GET
def api_starters(request):
    """Starter cards as JSON (mount clients that render their own UI)."""
    return JsonResponse({"starters": _starter_payload(), "default": DEFAULT_STARTER})


def _json_body(request):
    """Parse the request body as JSON, or (None, error_response)."""
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse(
            {"errors": ["Request body must be JSON."]}, status=400
        )
    if not isinstance(data, dict):
        return None, JsonResponse(
            {"errors": ["Request body must be a JSON object."]}, status=400
        )
    return data, None


@require_POST
def api_validate_input(request):
    """Validate wizard fields without touching the filesystem."""
    data, err = _json_body(request)
    if err is not None:
        return err
    assert data is not None
    errors = validate_create_input(
        data.get("label", ""), data.get("description", ""), data.get("starter", "")
    )
    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    return JsonResponse({"ok": True, "errors": []})


@require_POST
def api_create(request):
    """Scaffold a new app from a starter into a fresh directory."""
    from scitex_app.appmaker import init_app

    data, err = _json_body(request)
    if err is not None:
        return err
    assert data is not None
    label = (data.get("label") or "").strip()
    description = (data.get("description") or "").strip()
    starter_key = data.get("starter", "")
    errors = validate_create_input(label, description, starter_key)
    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    starter = STARTERS_BY_KEY[starter_key]
    target = data.get("target_dir") or str(Path.cwd() / target_slug(label))
    target_path = Path(target).expanduser()
    if not data.get("overwrite") and target_path.exists() and any(
        target_path.iterdir()
    ):
        return JsonResponse(
            {
                "success": False,
                "errors": [
                    f"Target directory is not empty: {target_path}. "
                    "Pick an empty directory or set overwrite."
                ],
            },
            status=400,
        )

    module = app_module_name(target_slug(label))
    created = init_app(
        target_dir=target_path,
        name=module,
        label=re.sub(r"[^\w ]", " ", label).strip() or "My",
        icon=starter.icon,
        description=description,
        manifest={
            "label": label,
            "starter": starter.key,
            "ai_hint": f"{starter.brief} {description}".strip(),
        },
        overwrite=bool(data.get("overwrite")),
    )
    agents_md = target_path / "AGENTS.md"
    if agents_md.is_file():
        with agents_md.open("a", encoding="utf-8") as fh:
            fh.write(starter_brief_section(starter, description))
    return JsonResponse(
        {
            "success": True,
            "project_dir": str(target_path.resolve()),
            "app_dir": str((target_path / module).resolve()),
            "module": module,
            "starter": starter.key,
            "files": created,
        }
    )


@require_POST
def api_validate_app(request):
    """Run ``validate_with_warnings`` on an existing app directory."""
    from scitex_app.appmaker import validate_with_warnings

    data, err = _json_body(request)
    if err is not None:
        return err
    assert data is not None
    app_dir = (data.get("app_dir") or "").strip()
    if not app_dir:
        return JsonResponse({"errors": ["app_dir is required."]}, status=400)
    try:
        errors, warnings = validate_with_warnings(app_dir)
    except Exception as exc:  # fail typed, never an HTML 500 page
        return JsonResponse({"errors": [f"Validation failed: {exc}"]}, status=500)
    return JsonResponse({"errors": errors, "warnings": warnings})


def _server_params(data):
    """Extract (app_dir, server_url, token) or an error response."""
    app_dir = (data.get("app_dir") or "").strip()
    server_url = (data.get("server_url") or "").strip()
    token = (data.get("token") or "").strip() or os.environ.get(
        "SCITEX_API_TOKEN", ""
    ).strip()
    missing = [
        name
        for name, val in (
            ("app_dir", app_dir),
            ("server_url", server_url),
            ("token", token),
        )
        if not val
    ]
    if missing:
        return None, JsonResponse(
            {"errors": [f"Missing required field(s): {', '.join(missing)}."]},
            status=400,
        )
    return (app_dir, server_url, token), None


@require_POST
def api_publish(request):
    """Submit an app for review via the engine's publish hook."""
    from scitex_app.appmaker._publish import publish

    data, err = _json_body(request)
    if err is not None:
        return err
    assert data is not None
    params, perr = _server_params(data)
    if perr is not None:
        return perr
    assert params is not None
    app_dir, server_url, token = params
    try:
        result = publish(app_dir, server_url=server_url, token=token)
    except Exception as exc:
        return JsonResponse({"errors": [f"Publish failed: {exc}"]}, status=500)
    return JsonResponse(result if isinstance(result, dict) else {"result": result})


@require_POST
def api_dev_install(request):
    """Dev-install an app on a server via the engine's dev-install hook."""
    from scitex_app.appmaker._dev_install import dev_install

    data, err = _json_body(request)
    if err is not None:
        return err
    assert data is not None
    params, perr = _server_params(data)
    if perr is not None:
        return perr
    assert params is not None
    app_dir, server_url, token = params
    try:
        result = dev_install(
            app_dir,
            server_url=server_url,
            token=token,
            owner=data.get("owner"),
            repo=data.get("repo"),
        )
    except Exception as exc:
        return JsonResponse({"errors": [f"Dev install failed: {exc}"]}, status=500)
    return JsonResponse(result if isinstance(result, dict) else {"result": result})


__all__ = [
    "api_create",
    "api_dev_install",
    "api_publish",
    "api_starters",
    "api_validate_app",
    "api_validate_input",
    "healthz",
    "index",
]

# EOF
