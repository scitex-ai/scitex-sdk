#!/usr/bin/env python3
"""{% app_static %} appends a content hash that changes with the file."""

import re

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        USE_I18N=True,
        LANGUAGE_CODE="en",
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
    )
    django.setup()

from django.template import Context, engines  # noqa: E402

from scitex_sdk.ui.templatetags import scitex_static  # noqa: E402


def _render(path):
    source = "{% load scitex_static %}{% app_static path %}"
    return engines["django"].from_string(source).template.render(Context({"path": path}))


@pytest.fixture
def asset(tmp_path):
    target = tmp_path / "app.js"
    target.write_text("console.log(1);")
    return target


def test_known_asset_gets_a_content_hash():
    # Arrange
    path = "scitex_sdk/ui/js/app/panes.js"
    # Act
    url = _render(path)
    # Assert
    assert re.fullmatch(r"/static/scitex_sdk/ui/js/app/panes\.js\?v=[0-9a-f]{12}", url)


def test_missing_asset_falls_back_to_plain_static():
    # Arrange
    path = "no/such/file.js"
    # Act
    url = _render(path)
    # Assert
    assert url == "/static/no/such/file.js"


def test_edit_changes_the_version(asset):
    # Arrange
    before = scitex_static.file_version(str(asset))
    asset.write_text("console.log(22);")
    # Act
    after = scitex_static.file_version(str(asset))
    # Assert
    assert before != after


def test_unchanged_file_keeps_its_version(asset):
    # Arrange
    first = scitex_static.file_version(str(asset))
    # Act
    second = scitex_static.file_version(str(asset))
    # Assert
    assert first == second
