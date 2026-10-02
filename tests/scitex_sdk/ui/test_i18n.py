#!/usr/bin/env python3
"""scitex_sdk.ui.i18n: a leaf app's djangojs catalog, embedded for the TS gettext module."""

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

from django.test import override_settings  # noqa: E402
from django.utils import translation  # noqa: E402

from scitex_sdk.ui.i18n import js_catalog, js_catalog_element_id  # noqa: E402

FIXTURE_APP = "tests.scitex_sdk.ui.i18n_fixture"
WITH_FIXTURE_APP = override_settings(
    USE_I18N=True,
    INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui", FIXTURE_APP],
)


@WITH_FIXTURE_APP
def test_js_catalog_translates_a_msgid_into_japanese():
    # Arrange
    language = "ja"
    # Act
    payload = js_catalog(FIXTURE_APP, language=language)
    # Assert
    assert payload["catalog"]["Save"] == "保存"


@WITH_FIXTURE_APP
def test_js_catalog_keeps_plural_forms_as_a_list():
    # Arrange
    language = "ja"
    # Act
    payload = js_catalog(FIXTURE_APP, language=language)
    # Assert
    assert payload["catalog"]["%s figure"] == ["%s 個の図"]


@WITH_FIXTURE_APP
def test_js_catalog_keys_a_context_message_like_django_pgettext():
    # Arrange
    language = "ja"
    # Act
    payload = js_catalog(FIXTURE_APP, language=language)
    # Assert
    assert payload["catalog"]["verb\x04Export"] == "書き出す"


@WITH_FIXTURE_APP
def test_js_catalog_reports_the_japanese_plural_expression():
    # Arrange
    language = "ja"
    # Act
    payload = js_catalog(FIXTURE_APP, language=language)
    # Assert
    assert payload["plural"] == "0"


@WITH_FIXTURE_APP
def test_js_catalog_is_empty_for_english():
    # Arrange
    language = "en"
    # Act
    payload = js_catalog(FIXTURE_APP, language=language)
    # Assert
    assert payload["catalog"] == {}


@WITH_FIXTURE_APP
def test_js_catalog_follows_the_active_language():
    # Arrange
    with translation.override("ja"):
        # Act
        payload = js_catalog(FIXTURE_APP)
    # Assert
    assert payload["language"] == "ja"


def test_js_catalog_element_id_is_derived_from_the_package():
    # Arrange
    package = "figrecipe._django"
    # Act
    element_id = js_catalog_element_id(package)
    # Assert
    assert element_id == "scitex-i18n-catalog-figrecipe--django"


@pytest.mark.parametrize("language", ["en", "ja", "fr"])
@pytest.mark.parametrize("msgid, japanese", [
    ("All Projects", "すべてのプロジェクト"),
    ("Could not select scope", "スコープを選択できませんでした"),
])
def test_picker_scope_catalog_preserves_translation_and_default(language, msgid, japanese):
    # Arrange
    package = "scitex_sdk.ui"
    expected = japanese if language == "ja" else msgid
    # Act
    payload = js_catalog(package, language=language)
    translated = payload["catalog"].get(msgid, msgid)
    # Assert
    assert translated == expected
