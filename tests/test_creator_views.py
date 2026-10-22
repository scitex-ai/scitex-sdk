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
                "BACKEND": "django.template.backends.DjangoTemplates",
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
    # Arrange
    return Client()


def test_index_renders_wizard(client):
    # Arrange
    # Act
    response = client.get("/")
    # Assert
    assert response.status_code == 200


def test_index_lists_starter_cards(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "Data entry form" in html


def test_index_mounts_shared_app_header(client):
    """The SDK App GUI uses the shared AppHeader primitive, like every leaf.

    No leaf-local <h1>: title/version flow through data-stx-app-header.
    """
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "data-stx-app-header" in html


def test_index_mounts_shared_app_header_script(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "scitex_sdk/ui/js/app/app-header.js" in html


def test_index_mounts_shared_app_header_without_leaf_title(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "<h1>Create a SciTeX app</h1>" not in html


def test_project_picker_helper_detects_the_host_tag_library():
    # Arrange
    from scitex_sdk.creator.views import _project_picker_available

    # Act
    available = _project_picker_available()
    # Assert
    assert available is True


def test_anonymous_index_renders_no_picker_markup(client):
    """Fail-soft: unsigned requests get plain wizard markup, no picker."""
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert '<div class="stx-app-project-selector"' not in html


def test_healthz_reports_ok(client):
    # Arrange
    # Act
    payload = json.loads(client.get("/healthz").content)
    # Assert
    assert payload == {
        "ok": True,
        "app": "scitex-sdk-creator",
    }


def test_starters_lists_four_cards(client):
    # Arrange
    # Act
    payload = json.loads(client.get("/api/starters").content)
    # Assert
    assert len(payload["starters"]) == 4


def test_validate_input_accepts_good_input(client):
    # Arrange
    # Act
    resp = client.post(
        "/api/validate-input",
        {"label": "My App", "description": "x", "starter": "blank"},
        content_type="application/json",
    )
    # Assert
    assert json.loads(resp.content)["ok"] is True


def test_validate_input_rejects_empty_label(client):
    # Arrange
    # Act
    resp = client.post(
        "/api/validate-input",
        {"label": "  ", "description": "x", "starter": "blank"},
        content_type="application/json",
    )
    # Assert
    assert resp.status_code == 400


def test_validate_input_rejects_unknown_starter(client):
    # Arrange
    # Act
    resp = client.post(
        "/api/validate-input",
        {"label": "My App", "description": "x", "starter": "nope"},
        content_type="application/json",
    )
    # Assert
    assert json.loads(resp.content)["errors"] != []


def test_create_scaffolds_app(client, tmp_path):
    # Arrange
    # Act
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
    # Assert
    assert json.loads(resp.content)["success"] is True


def test_create_writes_manifest(client, tmp_path):
    # Arrange
    target = tmp_path / "wizard-manifest-check"
    # Act
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
    # Assert
    assert (target / "wizard_manifest_app" / "manifest.json").is_file()


def test_create_reports_nested_app_dir(client, tmp_path):
    # Arrange
    target = tmp_path / "app-dir-check"
    # Act
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
    # Assert
    assert json.loads(resp.content)["app_dir"].endswith("app_dir_check_app")


def test_create_refuses_nonempty_dir(client, tmp_path):
    # Arrange
    (tmp_path / "occupied.txt").write_text("mine")
    # Act
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
    # Assert
    assert resp.status_code == 400


def test_validate_app_reports_scaffold_errors(client, tmp_path):
    # Arrange
    # Act
    resp = client.post(
        "/api/validate-app",
        {"app_dir": str(tmp_path)},
        content_type="application/json",
    )
    # Assert
    assert json.loads(resp.content)["errors"] != []


def test_validate_app_requires_app_dir(client):
    # Arrange
    # Act
    resp = client.post(
        "/api/validate-app", {}, content_type="application/json"
    )
    # Assert
    assert resp.status_code == 400


def test_publish_requires_server_token_fields(client, tmp_path):
    # Arrange
    # Act
    resp = client.post(
        "/api/publish",
        {"app_dir": str(tmp_path)},
        content_type="application/json",
    )
    # Assert
    assert resp.status_code == 400

# EOF
