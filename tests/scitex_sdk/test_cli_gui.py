#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for `scitex-sdk gui` (Click CliRunner, no server started).

State and configuration isolation use their real environment channels.
Default-option tests pin an owned empty YAML file; integration controls
exercise project/user discovery separately without touching user settings.
"""

from __future__ import annotations

import json
import os

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner

from scitex_sdk.app._gui_runtime import state_path, state_path_env_var
from scitex_sdk.cli import PACKAGE, main


@pytest.fixture
def runner():
    # Arrange
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_gui_configuration(tmp_path):
    keys = ("SCITEX_SDK_CONFIG", "SCITEX_SDK_GUI_HOST", "SCITEX_SDK_GUI_PORT")
    saved = {key: os.environ.get(key) for key in keys}
    path = tmp_path / "default-gui.yaml"
    path.write_text("gui: {}\n")
    for key in keys:
        os.environ.pop(key, None)
    os.environ["SCITEX_SDK_CONFIG"] = str(path)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture(autouse=True)
def isolated_state(tmp_path):
    # Arrange — real env-var swap (NM002-compliant), not monkeypatch.
    name = state_path_env_var(PACKAGE)
    original = os.environ.get(name)
    os.environ[name] = str(tmp_path / "gui.json")
    try:
        assert state_path(PACKAGE) == tmp_path / "gui.json"
        yield tmp_path / "gui.json"
    finally:
        if original is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original


def test_gui_help_exit_code_is_zero(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui", "--help"])
    # Assert
    assert result.exit_code == 0


def test_gui_help_lists_serve(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui", "--help"])
    # Assert
    assert "serve" in result.output


def test_gui_bare_requires_a_verb(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui"])
    # Assert
    assert result.exit_code == 2


def test_gui_serve_dry_run_names_the_port(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui", "serve", "--dry-run"])
    # Assert
    assert "31301" in result.output


def test_gui_serve_dry_run_json_shape(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui", "serve", "--dry-run", "--json"])
    # Assert
    assert json.loads(result.output)["would_serve"] is True


def test_gui_status_reports_not_running(runner, isolated_state):
    # Arrange
    isolated_state
    # Act
    result = runner.invoke(main, ["gui", "status"])
    # Assert
    assert "not running" in result.output


def test_gui_status_json_carries_running_flag(runner, isolated_state):
    # Arrange
    isolated_state
    # Act
    result = runner.invoke(main, ["gui", "status", "--json"])
    # Assert
    assert "running" in json.loads(result.output)


def test_gui_stop_reports_not_running(runner, isolated_state):
    # Arrange
    isolated_state
    # Act
    result = runner.invoke(main, ["gui", "stop"])
    # Assert
    assert "not running" in result.output


def test_gui_stop_dry_run_reports_not_running(runner, isolated_state):
    # Arrange
    isolated_state
    # Act
    result = runner.invoke(main, ["gui", "stop", "--dry-run"])
    # Assert
    assert "not running" in result.output


def test_gui_refuses_remote_bind(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["gui", "serve", "--host", "0.0.0.0"])
    # Assert
    assert result.exit_code != 0

# EOF
