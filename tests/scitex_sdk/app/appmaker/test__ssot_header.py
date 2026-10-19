#!/usr/bin/env python3
# Timestamp: 2026-10-19
# File: tests/scitex_sdk/app/appmaker/test__ssot_header.py

"""Scaffolded apps ship the shared SDK SSoT header row.

Port of scitex-app commit ccdb19a (card appcreator-ssot-header-row-20261017,
operator CCT4254): the App Creator scaffold emitted a leaf-local fork
(``{name}-header`` div, h2 1.5rem + subtitle, no version, no actions slot,
SDK sheet never linked). Every new app therefore disagreed with
Writer/Scholar/Stats/Storage about the header before its author wrote a line.

Adoption: the scaffold now emits the SDK row — ``.stx-app-header``
(scitex-sdk css/app/app-header.css) with title span + live leaf version
badge (absent when unknown), the canonical project-selector slot, and the
actions slot. The leaf owns the VALUES, the SDK owns the chrome.

Port note: ccdb19a touched five files; the fifth
(``_scaffold_agent_context.py``) has no counterpart fork here — the SDK
``_agents_md`` emits a short workflow doc with no header example, so it
never taught the fork and is left untouched. The two ``_agents_md``
assertions from the source test are dropped for the same reason (16 tests).

No mocks: generators are pure string builders; the tree test scaffolds
for real into a throwaway dir.

STX-TQ002 (AAA markers) + STX-TQ007 (one assert per test) compliant.
"""

from __future__ import annotations

from pathlib import Path

from scitex_sdk.app.appmaker._scaffold import init_app
from scitex_sdk.app.appmaker._scaffold_html import (
    _app_css,
    _index_partial_html,
    _tests_py,
    _views_py,
)

NAME = "demo_ssot_app"
LABEL = "Demo Ssot"


# ---------------------------------------------------------------------------
# Partial — the SDK row is emitted (one assert each)
# ---------------------------------------------------------------------------


def test_partial_links_sdk_app_header_css() -> None:
    # Arrange
    needle = "scitex_sdk/ui/css/app/app-header.css"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_has_shared_header_row() -> None:
    # Arrange
    needle = '<header class="stx-app-header '
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_has_title_span_with_label() -> None:
    # Arrange
    needle = f'<span class="stx-app-header__title">{LABEL}</span>'
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_version_badge_guarded_by_app_version() -> None:
    # Arrange
    needle = "{% if app_version %}"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_has_project_selector_slot() -> None:
    # Arrange
    needle = "stx-app-header__slot--project-selector"
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


def test_partial_has_actions_slot() -> None:
    # Arrange
    needle = '<div class="stx-app-header__actions"></div>'
    # Act
    partial = _index_partial_html(NAME, LABEL, "fas fa-flask")
    # Assert
    assert needle in partial


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
