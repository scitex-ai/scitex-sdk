#!/usr/bin/env python3
"""{% scitex_js_catalog %}: the json_script element the TS gettext module reads."""

import json

import django
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

from django.template import engines  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.utils import translation  # noqa: E402


FIXTURE_APP = "tests.scitex_sdk.ui.i18n_fixture"
WITH_FIXTURE_APP = override_settings(
    USE_I18N=True,
    INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui", FIXTURE_APP],
)


@WITH_FIXTURE_APP
def test_template_tag_embeds_the_catalog_as_json_script():
    # Arrange
    page = engines["django"].from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "tests.scitex_sdk.ui.i18n_fixture" %}'
    )
    with translation.override("ja"):
        html = page.render({})
    # Act
    embedded = json.loads(html.split(">", 1)[1].rsplit("</script>", 1)[0])
    # Assert
    assert embedded["catalog"]["Save"] == "保存"


@WITH_FIXTURE_APP
def test_template_tag_element_is_found_by_the_ts_reader_selector():
    # Arrange
    page = engines["django"].from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "tests.scitex_sdk.ui.i18n_fixture" %}'
    )
    # Act
    html = page.render({})
    # Assert
    assert html.startswith(
        '<script id="scitex-i18n-catalog-tests-scitex-sdk-ui-i18n-fixture" type="application/json">'
    )
