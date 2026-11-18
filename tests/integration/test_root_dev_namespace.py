"""Real SDK maintenance dispatch, retaining installed leaf implementations."""

import json
import os
import subprocess
import sys

import pytest

PROBE = r"""
import json, runpy, sys
if sys.argv[2] == "without-dev":
    from importlib.machinery import PathFinder
    class NoOptionalDev(PathFinder):
        @classmethod
        def find_spec(cls, fullname, path=None, target=None):
            if fullname == "scitex_dev" or fullname.startswith("scitex_dev."):
                return None
            return super().find_spec(fullname, path, target)
    sys.meta_path = [NoOptionalDev if finder is PathFinder else finder for finder in sys.meta_path]
def refuse(event, arguments):
    if event == "subprocess.Popen":
        argv = arguments[1]
        if len(argv) == 5 and argv[:2] == ["git", "-C"] and argv[3:] == ["rev-parse", "--show-toplevel"]:
            return  # Owning linter's read-only checkout discovery in this temp directory.
    if event in {"socket.connect", "socket.bind", "sqlite3.connect", "subprocess.Popen", "os.kill"}:
        raise RuntimeError("maintenance control refuses external/process/database effects")
sys.addaudithook(refuse)
sys.argv = ["scitex-sdk"] + json.loads(sys.argv[1])
runpy.run_module("scitex_sdk", run_name="__main__")
"""


def run_cli(tmp_path, arguments, *, without_dev=False):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            PROBE,
            json.dumps(arguments),
            "without-dev" if without_dev else "normal",
        ],
        cwd=tmp_path,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize("leaf", ["lint", "docs", "skills"])
def test_root_dev_leaf_help_is_reachable(tmp_path, leaf):
    result = run_cli(tmp_path, ["dev", leaf, "--help"])
    assert result.returncode == 0, result.stderr
    assert f"scitex-sdk dev {leaf}" in result.stdout


@pytest.mark.parametrize("name", ["04_cli-reference", "SKILL"])
def test_dev_skill_reads_same_owning_resource_as_existing_root_path(tmp_path, name):
    current = run_cli(tmp_path, ["dev", "skills", "get", name, "--json"])
    existing = run_cli(tmp_path, ["skills", "get", name, "--json"])
    assert current.returncode == existing.returncode == 0, current.stderr
    assert json.loads(current.stdout) == json.loads(existing.stdout)
    assert json.loads(current.stdout)["package"] == "scitex-sdk"


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("as_json", [False, True])
def test_dev_lint_retains_actual_leaf_findings_exit_and_coverage(
    tmp_path, dirty, as_json
):
    target = tmp_path / ("menu.html" if dirty else "theme.css")
    content = (
        "<select>" + "".join(f"<option>{i}</option>" for i in range(20)) + "</select>"
        if dirty
        else "body { color: var(--stx-text); }\n"
    )
    target.write_text(content)
    suffix = [str(target)] + (["--json"] if as_json else [])
    current = run_cli(tmp_path, ["dev", "lint", *suffix])
    existing = run_cli(tmp_path, ["ui", "lint", *suffix])
    assert current.returncode == existing.returncode == int(dirty), current.stderr
    assert current.stdout == existing.stdout
    assert target.read_text() == content
    if as_json:
        rows = [json.loads(line) for line in current.stdout.splitlines()]
        assert rows[0]["kind"] == "coverage"
        assert bool([r for r in rows if r.get("rule") == "STX-UI106"]) == dirty
    else:
        assert "NOT EVERYTHING WAS INSPECTED" in current.stdout


@pytest.mark.parametrize("arguments", [["dev", "--help"], ["dev", "lint", "--help"]])
def test_dev_lint_remains_available_without_optional_dev(tmp_path, arguments):
    result = run_cli(tmp_path, arguments, without_dev=True)
    assert result.returncode == 0, result.stderr
    assert "lint" in result.stdout


def test_dev_is_a_group_and_refuses_unknown_command(tmp_path):
    result = run_cli(tmp_path, ["dev", "not-a-command"])
    assert result.returncode == 2
    assert "No such command" in result.stderr


def test_command_objects_are_reused_without_mutating_component_tree():
    from scitex_sdk.cli import main
    from scitex_sdk.ui._cli import main as ui

    dev = main.commands["dev"]
    assert dev.commands["lint"] is ui.commands["lint"]
    assert dev.commands["docs"] is main.commands["docs"]
    assert dev.commands["skills"] is main.commands["skills"]
    assert "dev" in ui.commands and "lint" in ui.commands


def test_lint_help_has_real_option_spelling_and_current_sdk_routes(tmp_path):
    result = run_cli(tmp_path, ["dev", "lint", "--help"])
    assert result.returncode == 0, result.stderr
    assert "--treat-as-scitex-ui" in result.stdout
    assert "--treat-as-scitex-sdk ui" not in result.stdout
