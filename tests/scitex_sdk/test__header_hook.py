"""Executable source guards run against real Git/editor inputs."""

import json
import subprocess
import sys

from scitex_sdk._header_hook import check_payload
from scitex_sdk._hook_rules import provide


def test_proposed_write_is_checked_before_disk_mutation(tmp_path):
    # Arrange
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {
            "file_path": "leaf.css",
            "content": ".stx-app-header {height:80px}",
        },
    }
    # Act
    # Assert
    assert len(check_payload(payload)) == 1


def test_unverifiable_edit_fails_closed(tmp_path):
    # Arrange
    (tmp_path / "leaf.css").write_text("a {}")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "leaf.css",
            "old_string": "missing",
            "new_string": "x",
        },
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_sdk._header_hook"],
        check=False,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    # Assert
    assert result.returncode == 2


def test_shell_hook_inspects_actual_untracked_css(tmp_path):
    # Arrange
    # Act
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "commit",
            "--allow-empty",
            "-m",
            "baseline",
        ],
        check=True,
        capture_output=True,
    )
    (tmp_path / "leaf.css").write_text(".stx-app-project-selector {height:80px}")
    # Assert
    assert (
        len(
            check_payload(
                {
                    "cwd": str(tmp_path),
                    "tool_name": "Bash",
                    "tool_input": {"command": "true"},
                }
            )
        )
        == 1
    )


def test_existing_guard_is_preserved_and_scripts_exist():
    # Arrange
    from importlib.resources import files

    # Act
    rules = provide()
    # Assert
    assert (
        "sdk.no-unthemed-scrollbar" in {r.id for r in rules}
        and all(
            files("scitex_sdk").joinpath(r.script).is_file() for r in rules if r.script
        )
        and len([r for r in rules if r.severity == "deny"]) == 2
    )


def test_missing_scanner_denies_executable_hook(tmp_path):
    # Arrange
    import os
    import shutil
    from importlib.resources import files

    package = tmp_path / "scitex_sdk"
    shutil.copytree(str(files("scitex_sdk")), package)
    (package / "ui/_linter/_header_contract.py").unlink()
    shutil.rmtree(package / "ui/_linter/__pycache__", ignore_errors=True)
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": "leaf.css", "content": "a {}"},
    }
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_sdk._header_hook"],
        check=False,
        cwd=tmp_path,
        env=env,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    # Assert
    assert result.returncode == 2
