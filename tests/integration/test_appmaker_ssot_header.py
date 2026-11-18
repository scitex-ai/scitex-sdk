# Timestamp: 2026-10-19
# File: tests/scitex_sdk/app/appmaker/test__ssot_header.py

"""Generated apps delegate header rendering to the SDK component.

Exercise the actual Django output and registered picker tag. Labels and
optional versions are mount metadata; the SDK module builds title, picker,
and actions children. Generated consumers must not copy that child markup.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.template import Context, Template
from django.test import override_settings

from scitex_sdk.app.appmaker._scaffold import init_app
from scitex_sdk.app.appmaker._scaffold_html import (
    _app_css,
    _index_partial_html,
    _tests_py,
    _views_py,
)

NAME = "demo_ssot_app"
LABEL = "Demo Ssot"


class _RenderedMarkup(HTMLParser):
    """Collect actual rendered mount/script elements, excluding comments."""

    def __init__(self, source):
        super().__init__()
        self.mounts = []
        self.scripts = []
        self.pickers = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if "data-stx-app-header" in attributes:
            self.mounts.append((tag, attributes))
        if "data-stx-project-picker" in attributes:
            self.pickers.append(attributes)
        if tag == "script":
            self.scripts.append(attributes)


def _rendered(partial, *, version=None):
    html = Template(partial).render(
        Context({"app_scope": "user", "app_version": version})
    )
    return _RenderedMarkup(html)


# ---------------------------------------------------------------------------
# Partial — mount metadata delegates rendering to the SDK
# ---------------------------------------------------------------------------


def test_partial_links_sdk_app_header_css() -> None:
    # Arrange
    needle = "scitex_sdk/ui/css/app/app-header.css"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_renders_sdk_header_mount() -> None:
    # Arrange
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Act
    markup = _rendered(partial)
    # Assert
    assert [tag for tag, _ in markup.mounts] == ["div"]


def test_partial_supplies_title_as_renderer_metadata() -> None:
    # Arrange
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Act
    markup = _rendered(partial)
    # Assert
    assert markup.mounts[0][1]["data-app-title"] == LABEL


@pytest.mark.parametrize("version", [None, "1.2.3"])
def test_partial_supplies_optional_version_without_fake_badge(version) -> None:
    # Arrange
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Act
    markup = _rendered(partial, version=version)
    # Assert
    assert markup.mounts[0][1].get("data-app-version") == version


def test_partial_renders_real_sdk_picker_with_host_metadata() -> None:
    # Arrange
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    context = Context({"app_scope": "project", "current_project": "owned-project"})
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/owned-project-provider/"):
        markup = _RenderedMarkup(Template(partial).render(context))
    # Assert
    assert [
        (picker["data-provider-url"], picker["data-current"])
        for picker in markup.pickers
    ] == [("/owned-project-provider/", "owned-project")]


def test_partial_loads_sdk_module_to_render_header_children() -> None:
    # Arrange
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Act
    markup = _rendered(partial)
    # Assert
    assert any(
        script.get("type") == "module"
        and urlsplit(script.get("src", "")).path.endswith(
            "scitex_sdk/ui/js/app/app-header.js"
        )
        for script in markup.scripts
    )


# ---------------------------------------------------------------------------
# Partial + CSS — the fork is gone (one assert each)
# ---------------------------------------------------------------------------


def test_partial_has_no_forked_header_div() -> None:
    # Arrange
    needle = f"{NAME}-header"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle not in partial


def test_partial_has_no_h2_title() -> None:
    # Arrange
    needle = "<h2>"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle not in partial


def test_partial_has_no_subtitle() -> None:
    # Arrange
    needle = "subtitle"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle not in partial


def test_css_has_no_forked_header_rules() -> None:
    # Arrange
    needle = f".{NAME}-header"
    # Act
    css = _app_css(NAME, LABEL)
    # Assert
    assert needle not in css


def test_css_has_no_subtitle_rule() -> None:
    # Arrange
    needle = "subtitle"
    # Act
    css = _app_css(NAME, LABEL)
    # Assert
    assert needle not in css


# ---------------------------------------------------------------------------
# Views + generated tests — the badge source (one assert each)
# ---------------------------------------------------------------------------


def test_views_context_carries_app_version() -> None:
    # Arrange
    needle = '"app_version"'
    # Act
    views = _views_py(NAME, LABEL, "")
    # Assert
    assert needle in views


def test_views_version_reads_installed_dist() -> None:
    # Arrange
    needle = "importlib.metadata"
    # Act
    views = _views_py(NAME, LABEL, "")
    # Assert
    assert needle in views


def test_generated_tests_cover_header_version() -> None:
    # Arrange
    needle = "app_version"
    # Act
    tests_py = _tests_py(NAME, LABEL)
    # Assert
    assert needle in tests_py


# ---------------------------------------------------------------------------
# Emitted tree — the scaffolded partial carries the row (one assert each)
# ---------------------------------------------------------------------------


def test_emitted_partial_carries_sdk_row(tmp_path: Path) -> None:
    # Arrange
    init_app(target_dir=tmp_path, name=NAME, label=LABEL)
    candidate = tmp_path / NAME / "templates" / NAME / "index_partial.html"
    # Act
    text = candidate.read_text(encoding="utf-8")
    # Assert
    assert "stx-app-header" in text


def test_emitted_css_carries_no_fork(tmp_path: Path) -> None:
    # Arrange
    init_app(target_dir=tmp_path, name=NAME, label=LABEL)
    candidate = tmp_path / NAME / "static" / NAME / "css" / f"{NAME}.css"
    # Act
    text = candidate.read_text(encoding="utf-8")
    # Assert
    assert f".{NAME}-header" not in text
