#!/usr/bin/env python3
"""{% scitex_js_catalog %}: the json_script element the TS gettext module reads."""

import json
from html.parser import HTMLParser

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

from django.template import Context, Engine, engines  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.utils import translation  # noqa: E402
from django.utils.html import json_script  # noqa: E402

from scitex_sdk.ui.i18n import js_catalog, js_catalog_element_id  # noqa: E402


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


class _CatalogScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("id", "").startswith(
            "scitex-i18n-catalog-"
        ):
            self._current = [attributes["id"], ""]

    def handle_data(self, data):
        if self._current is not None:
            self._current[1] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._current is not None:
            element_id, contents = self._current
            self.scripts.append((element_id, json.loads(contents)))
            self._current = None


def _catalogs(html):
    parser = _CatalogScripts()
    parser.feed(html)
    return parser.scripts


def _document_engine(templates=None):
    return Engine(
        loaders=[
            ("django.template.loaders.locmem.Loader", templates or {}),
            "django.template.loaders.app_directories.Loader",
        ],
        libraries={
            "scitex_i18n": "scitex_sdk.ui.templatetags.scitex_i18n",
            "scitex_project_picker": "scitex_sdk.ui.templatetags.scitex_project_picker",
            "static": "django.templatetags.static",
            "i18n": "django.templatetags.i18n",
        },
    )


@pytest.mark.parametrize("language", ["en", "ja"])
def test_shared_shell_and_real_picker_emit_one_unchanged_ui_catalog(language):
    # Arrange
    page = _document_engine().from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% block app_content %}'
        '{% include "scitex_sdk/ui/_project_picker.html" %}'
        "{% endblock %}"
    )
    context = Context({"shell_lang": language, "provider_url": "/api/project-scope"})
    with translation.override(language):
        expected = js_catalog("scitex_sdk.ui")
        # Act
        html = page.render(context)
    # Assert
    assert (
        _catalogs(html) == [(js_catalog_element_id("scitex_sdk.ui"), expected)]
        and html.startswith("\n<!DOCTYPE html>")
        and html.count("data-stx-project-picker") == 1
    )


@pytest.mark.parametrize("language", ["en", "ja"])
def test_shared_shell_and_canonical_picker_tag_share_one_catalog(language):
    # Arrange
    page = _document_engine().from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% load scitex_project_picker %}{% block app_content %}'
        '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}'
        "{% endblock %}"
    )
    with translation.override(language):
        expected = js_catalog("scitex_sdk.ui")
        # Act
        html = page.render(Context({"shell_lang": language}))
    # Assert
    assert (
        _catalogs(html) == [(js_catalog_element_id("scitex_sdk.ui"), expected)]
        and html.count("data-stx-project-picker") == 1
    )


@pytest.mark.parametrize("language", ["en", "ja"])
def test_nested_and_include_only_pickers_share_outer_document_catalog(language):
    # Arrange
    engine = _document_engine(
        {
            "nested-picker.html": (
                '{% include "scitex_sdk/ui/_project_picker.html" only %}'
            ),
            "intermediate.html": '{% include "nested-picker.html" only %}',
        }
    )
    page = engine.from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% block app_content %}{% include "intermediate.html" only %}'
        '{% include "nested-picker.html" %}{% endblock %}'
    )
    with translation.override(language):
        # Act
        html = page.render(Context({"shell_lang": language}))
    # Assert
    assert len(_catalogs(html)) == 1 and html.count("data-stx-project-picker") == 2


@pytest.mark.parametrize("language", ["en", "ja"])
def test_picker_alone_keeps_original_catalog_markup_and_translation(language):
    # Arrange
    page = _document_engine().get_template("scitex_sdk/ui/_project_picker.html")
    with translation.override(language):
        expected = json_script(
            js_catalog("scitex_sdk.ui"), js_catalog_element_id("scitex_sdk.ui")
        )
        # Act
        html = page.render(Context({"provider_url": "/api/project-scope"}))
    # Assert
    assert html.count(expected) == 1 and len(_catalogs(html)) == 1


@pytest.mark.parametrize("language", ["en", "ja"])
def test_repeated_identical_tags_emit_one_catalog_in_one_document(language):
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "scitex_sdk.ui" %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    with translation.override(language):
        # Act
        html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 1


@pytest.mark.parametrize("language", ["en", "ja"])
def test_reused_context_and_cached_includes_emit_catalog_for_each_document(language):
    # Arrange
    engine = _document_engine()
    page = engine.from_string('{% include "scitex_sdk/ui/_project_picker.html" only %}')
    second_page = engine.from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% block app_content %}{% include "scitex_sdk/ui/_project_picker.html" %}'
        "{% endblock %}"
    )
    context = Context({"shell_lang": language})
    with translation.override(language):
        # Act
        documents = [
            page.render(context), page.render(context), second_page.render(context)
        ]
    # Assert
    assert [len(_catalogs(html)) for html in documents] == [1, 1, 1]


@override_settings(
    INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui", "scitex_sdk.app"]
)
@pytest.mark.parametrize("language", ["en", "ja"])
def test_distinct_real_package_catalogs_keep_ids_and_payloads(language):
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "scitex_sdk.ui" %}'
        '{% scitex_js_catalog "scitex_sdk.app" %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    with translation.override(language):
        expected = [
            (js_catalog_element_id(package), js_catalog(package))
            for package in ("scitex_sdk.ui", "scitex_sdk.app")
        ]
        # Act
        html = page.render(Context())
    # Assert
    assert _catalogs(html) == expected


def test_language_changes_and_later_reapplication_preserve_catalog_order():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n i18n %}'
        '{% language "ja" %}{% scitex_js_catalog "scitex_sdk.ui" %}{% endlanguage %}'
        '{% language "en" %}{% scitex_js_catalog "scitex_sdk.ui" %}{% endlanguage %}'
        '{% language "ja" %}{% scitex_js_catalog "scitex_sdk.ui" %}{% endlanguage %}'
    )
    expected = [
        (js_catalog_element_id("scitex_sdk.ui"), js_catalog("scitex_sdk.ui", language))
        for language in ("ja", "en", "ja")
    ]
    # Act
    html = page.render(Context())
    # Assert
    assert _catalogs(html) == expected


def test_captured_catalog_is_not_treated_as_emitted_markup():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "scitex_sdk.ui" as saved %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    # Act
    html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 1


def test_catalog_capture_after_emission_preserves_the_original_safe_string():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "scitex_sdk.ui" %}'
        '{% scitex_js_catalog "scitex_sdk.ui" as saved %}<section>{{ saved }}</section>'
    )
    # Act
    html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 2 and "<section><script" in html


def test_interpolated_capture_does_not_change_later_catalog_precedence():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n i18n %}'
        '{% language "ja" %}{% scitex_js_catalog "scitex_sdk.ui" %}{% endlanguage %}'
        '{% language "fr" %}{% scitex_js_catalog "scitex_sdk.ui" as saved %}'
        "{% endlanguage %}{{ saved }}"
        '{% language "ja" %}{% scitex_js_catalog "scitex_sdk.ui" %}{% endlanguage %}'
    )
    expected = [
        (js_catalog_element_id("scitex_sdk.ui"), js_catalog("scitex_sdk.ui", language))
        for language in ("ja", "fr", "ja")
    ]
    # Act
    html = page.render(Context())
    # Assert
    assert _catalogs(html) == expected


@pytest.mark.parametrize("language", ["en", "ja"])
def test_captured_picker_does_not_suppress_later_emitted_catalog(language):
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n scitex_project_picker %}'
        '{% scitex_project_picker scope="project" provider_url="/api/project-scope" as saved %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    with translation.override(language):
        expected = js_catalog("scitex_sdk.ui")
        # Act
        html = page.render(Context())
    # Assert
    assert (
        _catalogs(html) == [(js_catalog_element_id("scitex_sdk.ui"), expected)]
        and "data-stx-project-picker" not in html
    )


@override_settings(
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {"loaders": [("django.template.loaders.locmem.Loader", {})]},
    }]
)
def test_canonical_picker_uses_the_callers_real_sdk_template_engine():
    # Arrange
    page = _document_engine().from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% load scitex_project_picker %}{% block app_content %}'
        '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}'
        "{% endblock %}"
    )
    # Act
    html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 1 and html.count("data-stx-project-picker") == 1


@pytest.mark.parametrize("language", ["en", "ja"])
def test_canonical_pickers_inside_nested_include_only_share_shell_catalog(language):
    # Arrange
    engine = _document_engine({
        "nested-real-picker.html": (
            "{% load scitex_project_picker %}"
            '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}'
        ),
        "real-picker-wrapper.html": '{% include "nested-real-picker.html" only %}',
    })
    page = engine.from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% block app_content %}{% include "real-picker-wrapper.html" only %}'
        '{% include "nested-real-picker.html" only %}{% endblock %}'
    )
    with translation.override(language):
        # Act
        html = page.render(Context({"shell_lang": language}))
    # Assert
    assert len(_catalogs(html)) == 1 and html.count("data-stx-project-picker") == 2


@pytest.mark.parametrize("language", ["en", "ja"])
def test_real_picker_reused_context_keeps_a_catalog_in_each_separate_document(language):
    # Arrange
    engine = _document_engine()
    picker = engine.from_string(
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}'
    )
    shell = engine.from_string(
        '{% extends "scitex_sdk/ui/standalone_shell.html" %}'
        '{% load scitex_project_picker %}{% block app_content %}'
        '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}'
        "{% endblock %}"
    )
    context = Context({"shell_lang": language})
    with translation.override(language):
        # Act
        documents = [picker.render(context), shell.render(context), shell.render(context)]
    # Assert
    assert [len(_catalogs(html)) for html in documents] == [1, 1, 1]


@pytest.mark.parametrize("language", ["en", "ja"])
@pytest.mark.parametrize("buffered", [
    '{% scitex_js_catalog "scitex_sdk.ui" %}',
    '{% scitex_project_picker scope="project" provider_url="/api/project-scope" %}',
    '{% include "scitex_sdk/ui/_project_picker.html" only %}',
    '{% include "filtered-picker-wrapper.html" only %}',
])
def test_filtered_catalog_markup_keeps_later_real_json_catalog(language, buffered):
    # Arrange
    engine = _document_engine({
        "filtered-picker-wrapper.html": (
            '{% include "scitex_sdk/ui/_project_picker.html" only %}'
        ),
    })
    page = engine.from_string(
        "{% load scitex_i18n scitex_project_picker %}"
        "{% filter force_escape %}" + buffered + "{% endfilter %}"
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    with translation.override(language):
        expected = js_catalog("scitex_sdk.ui")
        # Act
        html = page.render(Context())
    # Assert
    assert (
        _catalogs(html) == [(js_catalog_element_id("scitex_sdk.ui"), expected)]
        and "&lt;script" in html
    )


@pytest.mark.parametrize("language", ["en", "ja"])
def test_filter_inside_included_template_preserves_later_catalog(language):
    # Arrange
    engine = _document_engine({
        "filtered-inner.html": (
            '{% filter force_escape %}'
            '{% include "scitex_sdk/ui/_project_picker.html" only %}{% endfilter %}'
        ),
    })
    page = engine.from_string(
        '{% load scitex_i18n %}{% include "filtered-inner.html" only %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    with translation.override(language):
        expected = js_catalog("scitex_sdk.ui")
        # Act
        html = page.render(Context())
    # Assert
    assert _catalogs(html) == [(js_catalog_element_id("scitex_sdk.ui"), expected)]


def test_filter_guard_is_document_scoped_when_context_and_templates_are_reused():
    # Arrange
    engine = _document_engine()
    filtered = engine.from_string(
        '{% load scitex_i18n %}{% filter force_escape %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}{% endfilter %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    direct = engine.from_string(
        '{% load scitex_i18n %}{% scitex_js_catalog "scitex_sdk.ui" %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    context = Context()
    # Act
    documents = [filtered.render(context), direct.render(context), filtered.render(context)]
    # Assert
    assert [len(_catalogs(html)) for html in documents] == [1, 1, 1]


def test_unrelated_filter_keeps_normal_direct_catalog_deduplication():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% filter force_escape %}<b>text</b>{% endfilter %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    # Act
    html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 1 and "&lt;b&gt;text&lt;/b&gt;" in html


def test_untransformed_filter_catalog_conservatively_preserves_later_output():
    # Arrange
    page = _document_engine().from_string(
        '{% load scitex_i18n %}{% filter default:"unused" %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}{% endfilter %}'
        '{% scitex_js_catalog "scitex_sdk.ui" %}'
    )
    # Act
    html = page.render(Context())
    # Assert
    assert len(_catalogs(html)) == 2
