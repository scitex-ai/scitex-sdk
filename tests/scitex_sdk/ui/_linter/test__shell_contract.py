"""Real shell CSS ownership and canonical native-dispatch fixtures."""

import json
import subprocess
import sys

import pytest
from scitex_dev._cli.audit._project._plugins import load_plugins
from scitex_dev._cli.audit._project._violation import Violation

from scitex_sdk.ui._linter._shell_contract import scan_shell


@pytest.mark.parametrize(
    "selector",
    [
        "#main-content[data-app-accent]",
        ".stx-shell-content",
        "[data-app-accent]",
        "#root",
    ],
)
def test_visible_top_stripe_is_rejected(tmp_path, selector):
    # Arrange
    (tmp_path / "app.css").write_text(
        selector
        + '::before {content:"";top:0!important;left:0;right:0;height:2px;background:var(--accent)}'
    )
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert len(findings) == 1


@pytest.mark.parametrize(
    "source",
    [
        ".workspace-content {width:90vw}",
        "#workspace-layout {max-width:1500px}",
        ".workspace-three-col {margin-inline:auto}",
        ".workspace-layout {background:purple}",
        "#workspace-three-col {min-width:800px}",
    ],
)
def test_leaf_cannot_fork_shared_frame(tmp_path, source):
    # Arrange
    (tmp_path / "leaf.css").write_text(source)
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert len(findings) == 1


@pytest.mark.parametrize(
    "source",
    [
        ".workspace-content .card {width:300px;background:red}",
        ".toolbar {border-top:2px solid navy}",
        'body::before {content:"";top:0;height:100vh;background:radial-gradient(red,blue)}',
        '#main-content::before {content:"";top:0;height:400px;background:radial-gradient(red,blue)}',
        "#root::before {content:none;top:0;left:0;right:0;height:2px;background:red}",
        "#root::before {display:none;top:0;left:0;right:0;height:2px;background:red}",
        '#root::before {content:"";bottom:0;height:2px;background:red}',
        '#main-content .interior::before {content:"";top:0;left:0;right:0;height:2px;background:red}',
        ".workspace-content {overflow:hidden;display:flex}",
        '#root::before {content:"";top:0;width:2px;height:2px;background:red}',
    ],
)
def test_interior_controls_and_backdrop_bubbles_are_allowed(tmp_path, source):
    # Arrange
    (tmp_path / "leaf.css").write_text(source)
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert findings == []


@pytest.mark.parametrize(
    "name",
    ["site-content-frame", "leaf-host-chrome", "global-base", "platform-backdrop"],
)
def test_exact_host_stylesheet_owns_frame(tmp_path, name):
    # Arrange
    (tmp_path / "pyproject.toml").write_text('[project]\nname="scitex-hub"\n')
    path = tmp_path / f"static/shared/css/layouts/{name}.css"
    path.parent.mkdir(parents=True)
    path.write_text(".workspace-content {width:90vw;background:var(--bg)}")
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert findings == []


@pytest.mark.parametrize(
    "distribution,path",
    [
        ("leaf-package", "static/shared/css/layouts/site-content-frame.css"),
        ("scitex-hub", "static/leaf/site-content-frame.css"),
        ("scitex-sdk", "static/shared/css/layouts/site-content-frame.css"),
    ],
)
def test_copied_owner_filename_does_not_grant_ownership(tmp_path, distribution, path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname="{distribution}"\n')
    destination = tmp_path / path
    destination.parent.mkdir(parents=True)
    destination.write_text(".workspace-content {background:red}")
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert len(findings) == 1


def test_canonical_sdk_file_cannot_restore_removed_stripe(tmp_path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text('[project]\nname="scitex-sdk"\n')
    destination = (
        tmp_path / "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/app-shell.css"
    )
    destination.parent.mkdir(parents=True)
    destination.write_text(
        '.stx-shell-content::after {content:"";top:0;left:0;right:0;height:2px;background:red}'
    )
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert len(findings) == 1


def test_project_dispatcher_reports_shell_error(tmp_path):
    # Arrange
    (tmp_path / "leaf.css").write_text(".workspace-layout {background:red}")
    # Act
    findings = []
    for check in load_plugins().checks:
        if check.__module__ == "scitex_sdk._audit_plugin":
            check(tmp_path, Violation, findings)
    # Assert
    assert [(f.rule, f.severity) for f in findings] == [("PS-SDK-SHELL", "E")]


def test_canonical_native_bridge_refuses_frame_fork(tmp_path):
    # Arrange
    payload = {
        "hook_event_name": "PreToolUse",
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "leaf.css",
            "content": ".workspace-content {width:40vw}",
        },
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_dev.hooks.dispatch", "--provider", "scitex-sdk"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    # Assert
    assert (result.returncode, "PS-SDK-SHELL" in result.stdout + result.stderr) == (
        2,
        True,
    )


@pytest.mark.parametrize(
    "path", ["components/workspace-layout.css", "components/workspace-chat-embed.css"]
)
def test_host_workspace_layout_and_embed_own_frame(tmp_path, path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text('[project]\nname="scitex-hub"\n')
    destination = tmp_path / "static/shared/css" / path
    destination.parent.mkdir(parents=True)
    destination.write_text(
        ".workspace-layout {background:var(--bg)} body.stx-embed .workspace-content {margin-left:0}"
    )
    # Act
    findings = scan_shell(tmp_path)
    # Assert
    assert findings == []
