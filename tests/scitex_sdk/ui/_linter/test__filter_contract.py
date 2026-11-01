"""Filter chrome fixtures exercise real source and native dispatch boundaries."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from scitex_dev._cli.audit._project._plugins import load_plugins
from scitex_dev._cli.audit._project._violation import Violation

from scitex_sdk._header_hook import check_payload
from scitex_sdk.ui._linter._filter_contract import scan_filters


@pytest.mark.parametrize(
    "source",
    [
        '<div class="agents-filter"><input><kbd>Ctrl+K</kbd></div>',
        '<button className="stx-filter-field__hint">Esc</button>',
        "<div data-stx-filter><input></div>",
        "<div data-stx-filter>Filter agents</div>",
        '<div class="agents-filter"><svg></svg><input></div>',
        '<div data-stx-filter style="padding:20px"></div>',
    ],
)
def test_handwritten_chrome_is_rejected(tmp_path, source):
    # Arrange
    (tmp_path / "view.tsx").write_text(source)
    # Act
    findings = scan_filters(tmp_path)
    # Assert
    assert findings


@pytest.mark.parametrize(
    "source",
    [
        ".stx-filter-field__input {font-size:18px}",
        "[data-stx-filter] {padding:22px}",
        ".agents-filter kbd {color:red}",
        ".agents-filter__hint {color:red}",
    ],
)
def test_local_chrome_styles_are_rejected(tmp_path, source):
    # Arrange
    (tmp_path / "app.css").write_text(source)
    # Act
    findings = scan_filters(tmp_path)
    # Assert
    assert len(findings) == 1


def test_empty_mount_and_leaf_result_filtering_are_allowed(tmp_path):
    # Arrange
    (tmp_path / "view.html").write_text(
        '<div data-stx-filter data-filter-subject="agents" data-filter-id="agents-filter"></div><input placeholder="Search DOI"><kbd>Ctrl+P</kbd>'
    )
    (tmp_path / "filter.js").write_text(
        'input.addEventListener("input", () => rows.filter(matches));'
    )
    (tmp_path / "content.css").write_text(
        ".results-filtered {display:none} .search-input {width:100%}"
    )
    # Act
    findings = scan_filters(tmp_path)
    # Assert
    assert findings == []


def test_only_exact_sdk_stylesheet_can_own_chrome(tmp_path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text('[project]\nname="scitex-sdk"\n')
    owner = tmp_path / "src/scitex_sdk/ui/static/scitex_sdk/ui/css/app/filter-field.css"
    owner.parent.mkdir(parents=True)
    owner.write_text(".stx-filter-field__hint {font-size:12px}")
    (tmp_path / "fork.css").write_text(".stx-filter-field__hint {font-size:24px}")
    # Act
    findings = scan_filters(tmp_path)
    # Assert
    assert [f.path for f in findings] == [str(tmp_path / "fork.css")]


def test_installed_project_dispatcher_reports_filter_error(tmp_path):
    # Arrange
    (tmp_path / "fork.css").write_text(".stx-filter-field__hint {color:red}")
    # Act
    findings = []
    for check in load_plugins().checks:
        if check.__module__ == "scitex_sdk._audit_plugin":
            check(tmp_path, Violation, findings)
    # Assert
    assert [(f.rule, f.severity) for f in findings] == [("PS-SDK-FILTER", "E")]


def test_existing_native_payload_command_checks_filters(tmp_path):
    # Arrange
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "fork.css",
            "content": ".stx-filter-field__hint {color:red}",
        },
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_sdk._header_hook"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    # Assert
    assert (
        result.returncode,
        "PS-SDK-FILTER" in result.stderr + result.stdout,
        (tmp_path / "fork.css").exists(),
    ) == (2, True, False)


def test_native_safe_edit_is_allowed(tmp_path):
    # Arrange
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "view.html",
            "content": "<div data-stx-filter></div>",
        },
    }
    # Act
    findings = check_payload(payload)
    # Assert
    assert findings == []


def test_actual_post_shell_changes_are_checked(tmp_path):
    # Arrange
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    (tmp_path / "fork.css").write_text(".stx-filter-field__hint {color:red}")
    # Act
    findings = check_payload(
        {"cwd": str(tmp_path), "tool_name": "Bash", "tool_input": {"command": "true"}}
    )
    # Assert
    assert any(f.startswith("PS-SDK-FILTER:") for f in findings)


def test_missing_filter_scanner_fails_closed(tmp_path):
    # Arrange
    import scitex_sdk

    package = tmp_path / "scitex_sdk"
    shutil.copytree(
        Path(scitex_sdk.__file__).parent,
        package,
        ignore=shutil.ignore_patterns("__pycache__", "static", "frontend"),
    )
    (package / "ui/_linter/_filter_contract.py").unlink()
    environment = dict(os.environ, PYTHONPATH=str(tmp_path))
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "view.html",
            "content": "<div data-stx-filter></div>",
        },
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_sdk._header_hook"],
        input=json.dumps(payload),
        env=environment,
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    # Assert
    assert (
        result.returncode,
        "verification failed (ModuleNotFoundError)" in result.stdout + result.stderr,
    ) == (2, True)


def test_real_dev_native_bridge_refuses_filter_fork(tmp_path):
    # Arrange
    payload = {
        "hook_event_name": "PreToolUse",
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "fork.css",
            "content": ".stx-filter-field__hint {color:red}",
        },
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_dev.hooks.dispatch", "--provider", "scitex-sdk"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    # Assert
    assert (result.returncode, "PS-SDK-FILTER" in result.stdout + result.stderr) == (
        2,
        True,
    )
