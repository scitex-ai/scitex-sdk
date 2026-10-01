#!/usr/bin/env python3
"""Tests for CLI commands."""

import json

import pytest

# click is an optional dep (scitex-ui[cli]); skip the whole module if it
# isn't installed so pytest collection stays green (PA-303).
pytest.importorskip("click")

from click.testing import CliRunner  # noqa: E402
from scitex_sdk.ui._cli import main  # noqa: E402


@pytest.fixture
def runner():
    return CliRunner()


def _invoke_json(runner, args):
    """Run a CLI command expecting a 0 exit and JSON stdout.

    Centralised so per-test bodies can keep a single behavioural assertion
    (STX-TQ007); a non-zero exit is surfaced via `pytest.fail` with the
    captured output so the failure mode is still loud.
    """
    result = runner.invoke(main, args)
    if result.exit_code != 0:
        pytest.fail(f"CLI {args!r} exited {result.exit_code}; output:\n{result.output}")
    return json.loads(result.output)


class TestCLIRoot:
    def test_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Assert
        assert result.exit_code == 0

    def test_help_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help"])
        # Assert
        assert "SciTeX UI" in result.output

    def test_no_args_shows_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main)
        # Assert
        assert result.exit_code == 0

    def test_no_args_shows_help_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main)
        # Assert
        assert "SciTeX UI" in result.output

    def test_help_recursive_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Assert
        assert result.exit_code == 0

    def test_help_recursive_contains_mcp(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--help-recursive"])
        # Assert
        assert "mcp" in result.output

    def test_version_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Assert
        assert result.exit_code == 0

    def test_version_contains_scitex_ui(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["--version"])
        # Assert
        assert "scitex-sdk ui" in result.output


# Bare `version` subcommand was removed (audit-cli §1b — `--version`/-V
# is the canonical flag). Coverage of the version surface is in
# TestCLIRoot.test_version.


class TestListPythonAPIs:
    def test_list_apis_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_contains_get_component(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis"])
        # Assert
        assert "get_component" in result.output

    def test_list_apis_verbose_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_verbose_shows_signatures(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "-v"])
        # Assert
        assert "(" in result.output  # signatures

    def test_list_apis_json_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["list-python-apis", "--json"])
        # Assert
        assert result.exit_code == 0

    def test_list_apis_json_module_is_scitex_ui(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        # Assert
        assert data["module"] == "scitex_sdk.ui"

    def test_list_apis_json_has_apis_key(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        # Assert
        assert "apis" in data

    def test_list_apis_json_get_component_in_names(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["list-python-apis", "--json"])
        names = [a["name"] for a in data["apis"]]
        # Assert
        assert "get_component" in names


# `list-components` subcommand is not yet implemented in scitex_sdk.ui._cli.
# Tests deferred until the surface lands.


class TestMCPGroup:
    def test_mcp_help_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_help_contains_start(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert "start" in result.output

    def test_mcp_help_contains_doctor(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "--help"])
        # Assert
        assert "doctor" in result.output

    def test_mcp_show_installation_exit_zero(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_contains_mcpservers(self, runner):
        # Canonical leaf is `show-installation` (§3 mcp install was renamed
        # but scitex-ui still uses the show-installation name).
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation"])
        # Assert
        assert "mcpServers" in result.output

    def test_mcp_show_installation_json_exit_zero(self, runner):
        # Arrange
        # Act
        result = runner.invoke(main, ["mcp", "show-installation", "--json"])
        # Assert
        assert result.exit_code == 0

    def test_mcp_show_installation_json_success_is_true(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert data["success"] is True

    def test_mcp_show_installation_json_has_scitex_ui(self, runner):
        # Arrange
        # Act
        data = _invoke_json(runner, ["mcp", "show-installation", "--json"])
        # Assert
        assert "scitex-ui" in data["config"]["mcpServers"]
