#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the creator wizard HTTP surface (Django test Client).

One assert per test. No mocks: api/create scaffolds into a real tmp
dir through the real engine; api/validate-app runs the real validator.
"""

from __future__ import annotations

import json

import django
import pytest
from django.conf import settings

if not settings.configured:
    _apps = [
        "django.contrib.staticfiles",
        "scitex_sdk.app",
        "scitex_sdk.creator",
    ]
    try:
        from scitex_sdk import ui as scitex_ui  # noqa: F401

        _apps.append("scitex_sdk.ui")
    except ImportError:
        pass
    settings.configure(
        SECRET_KEY="scitex-sdk-creator-tests",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF="scitex_sdk.creator.urls",
        INSTALLED_APPS=_apps,
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
            }
        ],
        DATABASES={},
        STATIC_URL="/static/",
    )
    django.setup()

from django.test import Client  # noqa: E402


@pytest.fixture
def client():
    return Client()


def test_index_renders_wizard(client):
    assert client.get("/").status_code == 200


def test_index_lists_starter_cards(client):
    assert "Data entry form" in client.get("/").content.decode()


def test_healthz_reports_ok(client):
    assert json.loads(client.get("/healthz").content) == {
        "ok": True,
        "app": "scitex-sdk-creator",
    }


def test_starters_lists_four_cards(client):
    assert len(json.loads(client.get("/api/starters").content)["starters"]) == 4


def test_validate_input_accepts_good_input(client):
    resp = client.post(
        "/api/validate-input",
        {"label": "My App", "description": "x", "starter": "blank"},
        content_type="application/json",
    )
    assert json.loads(resp.content)["ok"] is True


def test_validate_input_rejects_empty_label(client):
    resp = client.post(
        "/api/validate-input",
        {"label": "  ", "description": "x", "starter": "blank"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_validate_input_rejects_unknown_starter(client):
    resp = client.post(
        "/api/validate-input",
        {"label": "My App", "description": "x", "starter": "nope"},
        content_type="application/json",
    )
    assert json.loads(resp.content)["errors"] != []


def test_create_scaffolds_app(client, tmp_path):
    resp = client.post(
        "/api/create",
        {
            "label": "Wizard Test",
            "description": "from the wizard",
            "starter": "blank",
            "target_dir": str(tmp_path / "wizard-test"),
        },
        content_type="application/json",
    )
    assert json.loads(resp.content)["success"] is True


def test_create_writes_manifest(client, tmp_path):
    target = tmp_path / "wizard-manifest-check"
    client.post(
        "/api/create",
        {
            "label": "Wizard Manifest",
            "description": "from the wizard",
            "starter": "dashboard",
            "target_dir": str(target),
        },
        content_type="application/json",
    )
    assert (target / "wizard_manifest_app" / "manifest.json").is_file()


def test_create_reports_nested_app_dir(client, tmp_path):
    target = tmp_path / "app-dir-check"
    resp = client.post(
        "/api/create",
        {
            "label": "App Dir Check",
            "description": "x",
            "starter": "blank",
            "target_dir": str(target),
        },
        content_type="application/json",
    )
    assert json.loads(resp.content)["app_dir"].endswith("app_dir_check_app")


def test_create_refuses_nonempty_dir(client, tmp_path):
    (tmp_path / "occupied.txt").write_text("mine")
    resp = client.post(
        "/api/create",
        {
            "label": "Whatever",
            "description": "x",
            "starter": "blank",
            "target_dir": str(tmp_path),
        },
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_validate_app_reports_scaffold_errors(client, tmp_path):
    resp = client.post(
        "/api/validate-app",
        {"app_dir": str(tmp_path)},
        content_type="application/json",
    )
    assert json.loads(resp.content)["errors"] != []


def test_validate_app_requires_app_dir(client):
    resp = client.post(
        "/api/validate-app", {}, content_type="application/json"
    )
    assert resp.status_code == 400


def test_publish_requires_server_token_fields(client, tmp_path):
    resp = client.post(
        "/api/publish",
        {"app_dir": str(tmp_path)},
        content_type="application/json",
    )
    assert resp.status_code == 400

# EOF
