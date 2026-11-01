"""Real source fixtures for SDK header ownership."""

from pathlib import Path

import pytest

from scitex_sdk.ui._linter._header_contract import scan_headers


@pytest.mark.parametrize(
    "source",
    [
        ".stx-app-header__title {font-size:22px}",
        ".stx-app-project-selector__trigger {padding:8px}",
        "[data-stx-app-header] {height:64px}",
    ],
)
def test_direct_override_is_blocked(tmp_path, source):
    # Arrange
    (tmp_path / "leaf.css").write_text(source)
    # Act
    # Assert
    assert len(scan_headers(tmp_path)) == 1


def test_canonical_markup_is_allowed(tmp_path):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<header class="stx-app-header"><span class="stx-app-header__title">Stats</span></header>'
    )
    # Act
    # Assert
    assert scan_headers(tmp_path) == []


def test_forked_app_header_is_blocked(tmp_path):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<header class="stats-app-header">Stats</header>'
    )
    # Act
    # Assert
    assert len(scan_headers(tmp_path)) == 1


def test_inline_style_is_blocked(tmp_path):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<div data-stx-app-header style="font-size:22px"></div>'
    )
    # Act
    # Assert
    assert len(scan_headers(tmp_path)) == 1


def test_known_ancestor_button_override_is_blocked(tmp_path):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<div class="stx-creator"><div data-stx-app-header></div></div>'
    )
    (tmp_path / "leaf.css").write_text(".stx-creator button {padding:8px 16px}")
    # Act
    # Assert
    assert len(scan_headers(tmp_path)) == 1


@pytest.mark.parametrize(
    "source",
    [
        ".stx-creator .toolbar button {padding:8px}",
        ".unrelated button {padding:8px}",
        "/* .stx-app-header {height:64px} */",
        ".content:not(.stx-app-header *) {font-size:20px}",
    ],
)
def test_independent_controls_and_comments_are_allowed(tmp_path, source):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<div class="stx-creator"><div data-stx-app-header></div></div>'
    )
    (tmp_path / "leaf.css").write_text(source)
    # Act
    # Assert
    assert scan_headers(tmp_path) == []


def test_only_canonical_sdk_css_is_exempt(tmp_path):
    # Arrange
    owner = tmp_path / "src/scitex_sdk/ui/static/scitex_sdk/ui/css/app/app-header.css"
    owner.parent.mkdir(parents=True)
    owner.write_text(".stx-app-header {height:40px}")
    (owner.parent / "creator.css").write_text(".stx-app-header {height:80px}")
    # Act
    # Assert
    assert [Path(f.path).name for f in scan_headers(tmp_path)] == ["creator.css"]


@pytest.mark.parametrize(
    "source, count",
    [
        (
            '<script>const h=document.querySelector(".stx-app-header"); if(h) { h.focus(); }</script>',
            0,
        ),
        ("<style>.stx-app-project-selector {font-size:20px}</style>", 1),
    ],
)
def test_only_literal_stylesheets_are_scanned_in_markup(tmp_path, source, count):
    # Arrange
    (tmp_path / "page.html").write_text(source)
    # Act
    # Assert
    assert len(scan_headers(tmp_path)) == count
