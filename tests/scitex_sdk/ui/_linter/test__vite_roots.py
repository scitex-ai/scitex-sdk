"""Nested Vite provenance is static, bounded, and never hides authored CSS."""

import json
from pathlib import Path

import pytest

from scitex_sdk.ui._linter._header_contract import scan_headers
from scitex_sdk.ui._linter._shell_contract import scan_shell


def _project(
    root,
    *,
    directory="leaf/frontend",
    output="../static",
    command="tsc && vite build",
    config=None,
):
    project = root / directory
    project.mkdir(parents=True, exist_ok=True)
    (project / "package.json").write_text(json.dumps({"scripts": {"build": command}}))
    if config is not None and not config.startswith("import "):
        config = 'import {defineConfig} from "vite";\n' + config
    (project / "vite.config.ts").write_text(
        config
        or f"""import {{defineConfig}} from "vite";
export default defineConfig({{
 plugins: [react()],
 define: {{VERSION: JSON.stringify(version)}},
 build: {{outDir: "{output}", manifest: true, rollupOptions: {{input: resolve(__here, "index.html")}}}}
}});"""
    )
    (project / "index.html").write_text('<div id="root"></div>')
    base = (project / output).resolve()
    (base / ".vite").mkdir(parents=True, exist_ok=True)
    (base / "assets").mkdir(exist_ok=True)
    (base / "assets/index.css").write_text(
        ".stx-app-header{height:40px}.workspace-three-col{width:100%}"
    )
    (base / ".vite/manifest.json").write_text(
        json.dumps({"index.html": {"src": "index.html", "css": ["assets/index.css"]}})
    )
    return project, base


def test_nested_output_uses_static_build_context(tmp_path):
    # Arrange
    _project(tmp_path)
    # Act
    findings = scan_headers(tmp_path) + scan_shell(tmp_path)
    # Assert
    assert findings == []


@pytest.mark.parametrize(
    "command",
    [
        "cd elsewhere && vite build",
        "vite build --root ..",
        "vite build --config other.ts",
        "echo 'vite build'",
        "vite build # comment",
        "vite\nbuild",
        "vite\rbuild",
        "vite\r\nbuild",
        "vite\u2028build",
        "$(echo vite) build",
    ],
)
def test_unproven_build_cwd_cannot_hide_output(tmp_path, command):
    # Arrange
    _project(tmp_path, command=command)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]


@pytest.mark.parametrize(
    "config",
    [
        'export default defineConfig({root: elsewhere, build: {outDir: "../static", manifest: true}});',
        'export default defineConfig({...other, build: {outDir: "../static", manifest: true}});',
        'export default defineConfig({build: {...other, outDir: "../static", manifest: true}});',
        "export default defineConfig({build: {outDir: unknown, manifest: true}});",
        'export default defineConfig({build: {outDir: "../other", manifest: true}});',
        'export default defineConfig({build: {outDir: "../static", manifest: false}});',
        '/* export default defineConfig({build: {outDir: "../static", manifest: true}}); */',
        "const text = 'export default defineConfig({build: {outDir: \"../static\", manifest: true}});';",
        "export default defineConfig({build: {note: 'outDir: \"../static\", manifest: true'}});",
        'export default defineConfig({build: {outDir: "../static", manifest: true}, root: computeRoot()});',
        '/* export default defineConfig({build: {outDir: "../static", manifest: true}});',
        'const text = `export default defineConfig({build: {outDir: "../static", manifest: true}});`;',
        'export default defineConfig({build: {outDir: "../static", manifest: true}, build: unknown});',
        'export default compute(); export default defineConfig({build: {outDir: "../static", manifest: true}});',
        'import {defineConfig} from "other"; export default defineConfig({build: {outDir: "../static", manifest: true}});',
        'import {defineConfig} from "vite"; export default defineConfig({build: {outDir: "../static", manifest: true}}).other;',
        'import {defineConfig} from "vite"; export default defineConfig({build: {outDir: "../static", manifest: true}}, unknown);',
    ],
)
def test_unproven_or_spoofed_config_cannot_hide_output(tmp_path, config):
    # Arrange
    _project(tmp_path, config=config)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]


def test_nested_manifest_without_authored_input_is_inspected(tmp_path):
    # Arrange
    project, _ = _project(tmp_path)
    (project / "index.html").unlink()
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]


def test_ambiguous_nested_project_roots_are_not_chosen(tmp_path):
    # Arrange
    _project(tmp_path, directory="first", output="../output")
    _project(tmp_path, directory="second", output="../output")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]


def test_nested_authored_css_override_remains_inspected(tmp_path):
    # Arrange
    project, _ = _project(tmp_path)
    (project / "own.css").write_text(".stx-app-header{height:90px}")
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["own.css"]


def test_symlinked_config_cannot_bind_output(tmp_path):
    # Arrange
    project, _ = _project(tmp_path)
    config = project / "vite.config.ts"
    actual = project / "actual.ts"
    config.rename(actual)
    config.symlink_to(actual.name)
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]


@pytest.mark.parametrize("scripts", [None, "vite build", [], 1])
def test_unsupported_scripts_metadata_cannot_bind_output(tmp_path, scripts):
    # Arrange
    project, _ = _project(tmp_path)
    (project / "package.json").write_text(json.dumps({"scripts": scripts}))
    # Act
    findings = scan_headers(tmp_path)
    # Assert
    assert [Path(f.path).name for f in findings] == ["index.css"]
