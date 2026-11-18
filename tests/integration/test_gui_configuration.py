"""Real GUI CLI configuration in owned projects, without starting services."""

import json
import os
import subprocess
import sys

import pytest

from scitex_sdk.app._gui_runtime import state_path_env_var
from scitex_sdk.cli import PACKAGE

PROBE = r"""
import json, runpy, sys
def refuse(event, _args):
    if event == 'subprocess.Popen':
        sys.stderr.write('GUI_CHILD_COMMAND='+json.dumps(_args[1])+'\n')
        raise SystemExit(86)
    if event in {'socket.bind', 'socket.connect', 'sqlite3.connect',
                 'subprocess.Popen', 'os.kill'}:
        raise RuntimeError('GUI configuration control refuses side effects')
sys.addaudithook(refuse)
import scitex_sdk
sys.stderr.write('SDK_CLI_ORIGIN='+str(scitex_sdk.__file__)+'\n')
sys.argv = ['scitex-sdk'] + json.loads(sys.argv[1])
runpy.run_module('scitex_sdk', run_name='__main__')
"""


@pytest.fixture
def scenario(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        ["git", "init", "--quiet"], cwd=project, check=True, capture_output=True
    )
    work = project / "nested"
    work.mkdir()
    environment = dict(os.environ)
    for key in tuple(environment):
        if key == "SCITEX_SDK_CONFIG" or key.startswith("SCITEX_SDK_GUI_"):
            del environment[key]
    environment.update(
        SCITEX_DIR=str(tmp_path / "user"),
    )

    environment[state_path_env_var(PACKAGE)] = str(tmp_path / "gui-state.json")

    class Scenario:
        def __init__(self):
            self.project = project
            self.work = work
            self.environment = environment
            self.paths = {
                "user": tmp_path / "user/sdk/config.yaml",
                "project": project / ".scitex/sdk/config.yaml",
                "environment": tmp_path / "selected-environment.yaml",
                "explicit": tmp_path / "selected-explicit.yaml",
            }

        def write(self, name, text):
            path = self.paths[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return path

        def run(self, arguments):
            return subprocess.run(
                [sys.executable, "-c", PROBE, json.dumps(arguments)],
                cwd=self.work,
                env=self.environment,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

    return Scenario()


@pytest.mark.parametrize("verb", ["serve", "open"])
@pytest.mark.parametrize(
    "level,expected",
    [
        (0, ("127.0.0.1", 31301)),
        (1, ("localhost", 32101)),
        (2, ("127.0.0.1", 32102)),
        (3, ("::1", 32103)),
        (4, ("localhost", 32104)),
        (5, ("127.0.0.1", 32105)),
        (6, ("localhost", 32106)),
    ],
)
def test_path_and_value_precedence(scenario, verb, level, expected):
    arguments = ["gui"]
    if level >= 1:
        scenario.environment.update(
            SCITEX_SDK_GUI_HOST="localhost", SCITEX_SDK_GUI_PORT="32101"
        )
    for index, name, host in [
        (2, "user", "127.0.0.1"),
        (3, "project", "::1"),
        (4, "environment", "localhost"),
        (5, "explicit", "127.0.0.1"),
    ]:
        if level >= index:
            scenario.write(name, f"gui:\n  host: {host!r}\n  port: {32100 + index}\n")
    if level >= 4:
        scenario.environment["SCITEX_SDK_CONFIG"] = str(scenario.paths["environment"])
    if level >= 5:
        arguments += ["--config", str(scenario.paths["explicit"])]
    arguments += [verb, "--dry-run", "--json"]
    if level >= 6:
        arguments += ["--host", "localhost", "--port", "32106"]
    before = {
        name: path.read_bytes()
        for name, path in scenario.paths.items()
        if path.exists()
    }
    result = scenario.run(arguments)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert (data["host"], data["port"]) == expected
    assert {name: scenario.paths[name].read_bytes() for name in before} == before
    if level == 0:
        assert not scenario.paths["user"].exists()


@pytest.mark.parametrize("verb", ["serve", "open"])
def test_precedence_is_per_option_and_direct_cli_wins_invalid_environment(
    scenario, verb
):
    scenario.write("user", "gui:\n  host: localhost\n")
    scenario.environment.update(SCITEX_SDK_GUI_PORT="invalid-private-value")
    result = scenario.run(["gui", verb, "--dry-run", "--json", "--port", "32120"])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert (data["host"], data["port"]) == ("localhost", 32120)


def test_nearest_git_boundary_prevents_outer_project_config(scenario):
    scenario.write("user", "gui: {port: 32121}\n")
    scenario.write("project", "gui: {port: 32122}\n")
    subprocess.run(
        ["git", "init", "--quiet"], cwd=scenario.work, check=True, capture_output=True
    )
    result = scenario.run(["gui", "serve", "--dry-run", "--json"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["port"] == 32121


def test_project_config_symlink_is_read_without_replacement(scenario):
    target = scenario.write("explicit", "gui: {port: 32123}\n")
    link = scenario.paths["project"]
    link.parent.mkdir(parents=True)
    link.symlink_to(target)
    result = scenario.run(["gui", "serve", "--dry-run", "--json"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["port"] == 32123
    assert link.is_symlink() and target.read_text() == "gui: {port: 32123}\n"


def test_unrelated_cwd_yaml_is_not_automatically_loaded(scenario):
    (scenario.work / "config.yaml").write_text("PRIVATE-FIXTURE-CONTENT: [\n")
    result = scenario.run(["gui", "serve", "--dry-run", "--json"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["port"] == 31301


@pytest.mark.parametrize(
    "text,expected",
    [
        ("[]", "YAML mapping"),
        ("gui: []", "must be a mapping"),
        ("gui: null", "must be a mapping"),
        ("gui: {host: false}", "host must"),
        ("gui: {port: true}", "YAML integer"),
        ("gui: {port: '32101'}", "YAML integer"),
        ("gui: {port: 0}", "1 to 65535"),
        ("gui: {port: 65536}", "1 to 65535"),
        ("gui: {host: ' localhost '}", "surrounding whitespace"),
        ("gui: {allow_remote: true}", "only host and port"),
        ("gui: {force: true}", "only host and port"),
        ("PRIVATE-FIXTURE-CONTENT: [", "Cannot read SDK GUI configuration"),
    ],
)
def test_invalid_gui_configuration_refuses_without_exposing_values(
    scenario, text, expected
):
    path = scenario.write("explicit", text)
    result = scenario.run(
        ["gui", "--config", str(path), "serve", "--dry-run", "--json"]
    )
    assert result.returncode != 0
    assert expected in result.stderr
    assert "PRIVATE-FIXTURE-CONTENT" not in result.stdout + result.stderr


@pytest.mark.parametrize("selection", ["explicit", "environment", "broken-link"])
def test_explicit_missing_or_broken_file_does_not_fall_back(scenario, selection):
    scenario.write("user", "gui: {port: 32130}\n")
    path = scenario.paths["explicit"]
    arguments = ["gui"]
    if selection == "environment":
        scenario.environment["SCITEX_SDK_CONFIG"] = str(path)
    else:
        if selection == "broken-link":
            path.symlink_to(path.parent / "absent-target")
        arguments += ["--config", str(path)]
    result = scenario.run(arguments + ["serve", "--dry-run"])
    assert result.returncode != 0
    assert "Cannot read SDK GUI configuration" in result.stderr


@pytest.mark.parametrize("verb", ["serve", "open"])
def test_yaml_remote_host_still_requires_explicit_allow_remote(scenario, verb):
    scenario.write("user", "gui: {host: '0.0.0.0', port: 32131}\n")
    scenario.environment["SCITEX_SDK_GUI_ALLOW_REMOTE"] = "true"
    refused = scenario.run(["gui", verb, "--dry-run", "--json"])
    allowed = scenario.run(["gui", verb, "--dry-run", "--json", "--allow-remote"])
    assert refused.returncode != 0 and "Refusing non-loopback" in refused.stderr
    assert allowed.returncode == 0, allowed.stderr
    assert json.loads(allowed.stdout)["host"] == "0.0.0.0"


def test_force_remains_an_explicit_cli_flag(scenario):
    scenario.environment["SCITEX_SDK_GUI_FORCE"] = "true"
    plain = scenario.run(["gui", "serve", "--dry-run", "--json"])
    explicit = scenario.run(["gui", "serve", "--dry-run", "--json", "--force"])
    assert plain.returncode == explicit.returncode == 0
    assert json.loads(plain.stdout)["force"] is False
    assert json.loads(explicit.stdout)["force"] is True


def test_open_propagates_explicit_configuration_to_child(scenario):
    selected = scenario.write("explicit", "gui: {host: localhost, port: 32140}\n")
    damaged = scenario.write("environment", "PRIVATE-FIXTURE-CONTENT: [")
    scenario.environment["SCITEX_SDK_CONFIG"] = str(damaged)
    result = scenario.run(["gui", "--config", str(selected), "open", "--no-browser"])
    assert result.returncode == 86, result.stderr
    line = next(
        line
        for line in result.stderr.splitlines()
        if line.startswith("GUI_CHILD_COMMAND=")
    )
    command = json.loads(line.partition("=")[2])
    assert command[:3] == [sys.executable, "-m", "scitex_sdk"]
    child = scenario.run(command[3:] + ["--dry-run", "--json"])
    assert child.returncode == 0, child.stderr
    assert (json.loads(child.stdout)["host"], json.loads(child.stdout)["port"]) == (
        "localhost",
        32140,
    )


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize(
    "arguments",
    [
        ["gui", "--help"],
        ["gui", "serve", "--help"],
        ["gui", "status", "--json"],
        ["gui", "stop", "--dry-run"],
    ],
)
def test_help_and_state_recovery_ignore_damaged_configuration(
    scenario, arguments, explicit
):
    path = scenario.write("explicit", "PRIVATE-FIXTURE-CONTENT: [")
    scenario.environment["SCITEX_SDK_CONFIG"] = str(path)
    if explicit:
        arguments = ["gui", "--config", str(path)] + arguments[1:]
    result = scenario.run(arguments)
    assert result.returncode == 0, result.stderr
    assert "PRIVATE-FIXTURE-CONTENT" not in result.stdout + result.stderr
