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


def test_sdk_mount_markup_is_allowed(tmp_path):
    # Arrange
    (tmp_path / "page.html").write_text(
        '<div data-stx-app-header data-app-title="Stats"></div>'
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
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "scitex-sdk"\n')
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


def test_consumer_cannot_claim_owner_by_copying_sdk_paths(tmp_path):
    # Arrange
    path = tmp_path / "src/scitex_sdk/ui/static/scitex_sdk/ui/css/app/app-header.css"
    path.parent.mkdir(parents=True)
    path.write_text(".stx-app-header {font-size:80px}")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "consumer"\n')
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert len(findings) == 1


def _write_vite_output(root):
    """Create actual imported SDK CSS output and its Vite manifest."""
    base = root / "src/app/static/app"
    (base / ".vite").mkdir(parents=True)
    (base / "assets").mkdir()
    (base / ".vite/manifest.json").write_text(
        '{"src/app/frontend/src/leaf.css":{"file":"assets/index.css"}}'
    )
    (base / "assets/index.css").write_text(".stx-app-header{height:40px}")


def test_vite_output_without_authored_inputs_is_still_inspected(tmp_path):
    # Arrange
    _write_vite_output(tmp_path)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert len(findings) == 1


def test_vite_output_with_authored_inputs_defers_to_actual_source(tmp_path):
    # Arrange
    _write_vite_output(tmp_path)
    source = tmp_path / "src/app/frontend/src/leaf.css"
    source.parent.mkdir(parents=True)
    source.write_text(".toolbar{height:40px}")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert findings == []


@pytest.mark.parametrize(
    "source",
    [
        '<header class="stx-app-header">Stats</header>',
        '<header className="stx-app-header">Stats</header>',
        "<header data-stx-app-header>Stats</header>",
        '<div className="stx-app-header__title">Stats</div>',
    ],
)
def test_handwritten_canonical_classes_do_not_bypass_renderer_ownership(
    tmp_path, source
):
    # Arrange
    (tmp_path / "page.html").write_text(source)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert len(findings) == 1


@pytest.mark.parametrize(
    "declaration, expected", [("display:none", 0), ("font-size:22px", 1)]
)
def test_leaf_slot_visibility_is_allowed_without_style_ownership(
    tmp_path, declaration, expected
):
    # Arrange
    (tmp_path / "leaf.css").write_text(
        ".stx-app-header__slot--project-selector [data-own-project] {"
        + declaration
        + "}"
    )
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert len(findings) == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ('<button class="stx-app-project-selector__trigger">Pick</button>', 1),
        ('<button className="stx-app-project-selector__option">All</button>', 1),
        ('<input class="stx-app-project-selector__search" />', 1),
        ('<div class="stx-app-project-selector" data-stx-project-picker></div>', 0),
    ],
)
def test_project_picker_children_are_owned_by_sdk_renderer(tmp_path, source, expected):
    # Arrange
    (tmp_path / "page.html").write_text(source)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert len(findings) == expected


def test_gitignored_user_data_is_not_project_source_context(tmp_path):
    # Arrange
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    (tmp_path / ".gitignore").write_text("data/\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/user-manuscript.html").write_bytes(b"\xff")
    source = tmp_path / "leaf.css"
    source.write_text(".toolbar{}")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert findings == []


def test_explicit_ignored_editor_target_is_still_checked(tmp_path):
    # Arrange
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    (tmp_path / ".gitignore").write_text("local.css\n")
    path = tmp_path / "local.css"
    # Act
    findings = scan_headers(
        tmp_path, overlays={path: ".stx-app-header{font-size:80px}"}, targets={path}
    )
    # Assert
    assert len(findings) == 1
