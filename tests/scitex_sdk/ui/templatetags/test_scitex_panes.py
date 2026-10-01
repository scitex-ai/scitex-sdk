#!/usr/bin/env python3
"""{% scitex_panes %} / {% scitex_pane %} render the panes markup contract."""

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

from django.template import Context, TemplateSyntaxError, engines  # noqa: E402

PANES = (
    "{% load i18n scitex_panes %}"
    '{% scitex_panes "figrecipe" columns="280px 1fr" active="plot" %}'
    '{% scitex_pane "data" label=_("Data") icon="D" order=1 %}<p>rows</p>{% endscitex_pane %}'
    '{% scitex_pane "plot" label=title order=2 %}<p>chart</p>{% endscitex_pane %}'
    "{% endscitex_panes %}"
)


def _render(source=PANES, context=None):
    template = engines["django"].from_string(source).template
    return template.render(Context(context or {"title": "Plot <b>"}))


def test_root_declares_the_app():
    # Arrange
    expected = 'data-stx-panes="figrecipe"'
    # Act
    html = _render()
    # Assert
    assert expected in html


def test_root_carries_the_desktop_columns():
    # Arrange
    expected = 'style="--stx-panes-columns: 280px 1fr"'
    # Act
    html = _render()
    # Assert
    assert expected in html


def test_root_carries_the_initial_pane():
    # Arrange
    expected = 'data-stx-active="plot"'
    # Act
    html = _render()
    # Assert
    assert expected in html


def test_pane_renders_id_label_icon_and_order():
    # Arrange
    expected = (
        '<section data-stx-pane="data" data-stx-label="Data" data-stx-icon="D" '
        'data-stx-order="1"><p>rows</p></section>'
    )
    # Act
    html = _render()
    # Assert
    assert expected in html


def test_pane_label_is_escaped():
    # Arrange
    expected = 'data-stx-label="Plot &lt;b&gt;"'
    # Act
    html = _render()
    # Assert
    assert expected in html


def test_wrapper_loads_the_panes_script():
    # Arrange
    expected = re.compile(r'<script type="module" src="/static/scitex_sdk/ui/js/app/panes\.js\?v=[0-9a-f]{12}"></script>')
    # Act
    html = _render()
    # Assert
    assert expected.search(html)


def test_wrapper_loads_the_panes_stylesheet():
    # Arrange
    expected = re.compile(r'<link rel="stylesheet" href="/static/scitex_sdk/ui/css/app/panes\.css\?v=[0-9a-f]{12}">')
    # Act
    html = _render()
    # Assert
    assert expected.search(html)


def test_unknown_argument_is_a_syntax_error():
    # Arrange
    source = '{% load scitex_panes %}{% scitex_panes "a" colums="1fr" %}{% endscitex_panes %}'
    # Act
    template = engines["django"]
    # Assert
    with pytest.raises(TemplateSyntaxError, match="colums"):
        template.from_string(source)
