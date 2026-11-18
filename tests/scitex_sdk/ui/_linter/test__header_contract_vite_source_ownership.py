"""Vite build ownership follows real manifest inputs, not folder conventions."""

import json
import subprocess
from pathlib import Path

import pytest

from scitex_sdk.ui._linter._header_contract import scan_headers


def _build(root, source, *, manifest_source=None):
    source_path = root / source
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        "export {};" if source_path.suffix == ".ts" else ".toolbar{}"
    )
    base = root / "staticfiles/vite"
    (base / ".vite").mkdir(parents=True)
    (base / "assets").mkdir()
    output = base / "assets/bridge.css"
    output.write_text(".stx-app-header{height:40px}")
    entry = source if manifest_source is None else manifest_source
    manifest = base / ".vite/manifest.json"
    manifest.write_text(
        json.dumps({entry: {"src": entry, "css": ["assets/bridge.css"]}})
    )
    return source_path, output, manifest


def test_hub_static_ts_input_binds_actual_manifest_output(tmp_path):
    # Arrange
    _build(tmp_path, "apps/infra/public_app/static/public_app/ts/index.ts")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert findings == []


@pytest.mark.parametrize(
    "claimed", ["missing.ts", "../foreign.ts", "/outside/input.ts"]
)
def test_unbound_or_outside_manifest_cannot_hide_css(tmp_path, claimed):
    # Arrange
    _build(tmp_path, "apps/static/ts/index.ts", manifest_source=claimed)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["bridge.css"]


def test_gitignored_input_cannot_bind_manifest(tmp_path):
    # Arrange
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    _build(tmp_path, "private/input.ts")
    (tmp_path / ".gitignore").write_text("private/\n")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["bridge.css"]


def test_symlinked_input_cannot_bind_manifest(tmp_path):
    # Arrange
    source, _, _ = _build(tmp_path, "apps/static/ts/index.ts")
    actual = source.with_name("actual.ts")
    source.rename(actual)
    source.symlink_to(actual.name)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["bridge.css"]


def test_authored_override_remains_visible_beside_bundle(tmp_path):
    # Arrange
    _build(tmp_path, "apps/static/ts/index.ts")
    override = tmp_path / "apps/static/override.css"
    override.write_text(".stx-app-header{height:80px}")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["override.css"]


def test_manifest_cannot_suppress_its_authored_css_input(tmp_path):
    # Arrange
    source, _, manifest = _build(tmp_path, "apps/static/style.css")
    source.write_text(".stx-app-header{height:80px}")
    manifest.write_text(
        json.dumps(
            {
                source.relative_to(tmp_path).as_posix(): {
                    "src": source.relative_to(tmp_path).as_posix(),
                    "css": ["../../apps/static/style.css"],
                }
            }
        )
    )
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert sorted(Path(f.path).name for f in findings) == ["bridge.css", "style.css"]


def test_manifest_output_escape_is_not_suppressed(tmp_path):
    # Arrange
    _, _, manifest = _build(tmp_path, "apps/static/ts/index.ts")
    outside = tmp_path / "outside.css"
    outside.write_text(".stx-app-header{height:80px}")
    manifest.write_text(
        json.dumps(
            {
                "apps/static/ts/index.ts": {
                    "src": "apps/static/ts/index.ts",
                    "css": ["../../outside.css"],
                }
            }
        )
    )
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert sorted(Path(f.path).name for f in findings) == ["bridge.css", "outside.css"]


def test_external_bridge_output_belongs_to_build_with_real_hub_input(tmp_path):
    # Arrange
    _, _, manifest = _build(
        tmp_path, "apps/infra/public_app/static/public_app/ts/bridge-init.ts"
    )
    entries = json.loads(manifest.read_text())
    entries["../figrecipe/src/figrecipe/_django/frontend/src/workspace.ts"] = {
        "src": "../figrecipe/src/figrecipe/_django/frontend/src/workspace.ts",
        "css": ["assets/figrecipe-bridge-init-DVgpCSf1.css"],
    }
    manifest.write_text(json.dumps(entries))
    (manifest.parent.parent / "assets/figrecipe-bridge-init-DVgpCSf1.css").write_text(
        ".stx-app-header__title{font-size:14px}"
    )
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert findings == []


def test_unlisted_output_is_still_checked(tmp_path):
    # Arrange
    _, output, _ = _build(tmp_path, "apps/static/ts/index.ts")
    output.with_name("unlisted.css").write_text(".stx-app-header{height:80px}")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["unlisted.css"]


def test_authored_css_inside_build_directory_cannot_be_hidden(tmp_path):
    # Arrange
    source, _, manifest = _build(tmp_path, "staticfiles/vite/source.css")
    source.write_text(".stx-app-header{height:80px}")
    manifest.write_text(
        json.dumps(
            {
                "staticfiles/vite/source.css": {
                    "src": "staticfiles/vite/source.css",
                    "css": ["source.css", "assets/bridge.css"],
                }
            }
        )
    )
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["source.css"]
