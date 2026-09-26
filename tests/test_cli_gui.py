#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for `scitex-sdk gui` (Click CliRunner, no server started).

One assert per test. State isolation uses the documented env-var
channel (SCITEX_SDK_GUI_STATE), not mocks — the sanctioned path for
driving the real CLI without touching the developer's runtime state.
"""

from __future__ import annotations

import json

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner

from scitex_sdk.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SCITEX_SDK_GUI_STATE", str(tmp_path / "gui.json"))


def test_gui_help_exit_code_is_zero(runner):
    assert runner.invoke(main, ["gui", "--help"]).exit_code == 0


def test_gui_help_lists_serve(runner):
    assert "serve" in runner.invoke(main, ["gui", "--help"]).output


def test_gui_bare_requires_a_verb(runner):
    assert runner.invoke(main, ["gui"]).exit_code == 2


def test_gui_serve_dry_run_names_the_port(runner):
    result = runner.invoke(main, ["gui", "serve", "--dry-run"])
    assert "31301" in result.output


def test_gui_serve_dry_run_json_shape(runner):
    result = runner.invoke(main, ["gui", "serve", "--dry-run", "--json"])
    assert json.loads(result.output)["would_serve"] is True


def test_gui_status_reports_not_running(runner, isolated_state):
    assert "not running" in runner.invoke(main, ["gui", "status"]).output


def test_gui_status_json_carries_running_flag(runner, isolated_state):
    result = runner.invoke(main, ["gui", "status", "--json"])
    assert "running" in json.loads(result.output)


def test_gui_stop_reports_not_running(runner, isolated_state):
    assert "not running" in runner.invoke(main, ["gui", "stop"]).output


def test_gui_stop_dry_run_reports_not_running(runner, isolated_state):
    result = runner.invoke(main, ["gui", "stop", "--dry-run"])
    assert "not running" in result.output


def test_gui_refuses_remote_bind(runner):
    result = runner.invoke(main, ["gui", "serve", "--host", "0.0.0.0"])
    assert result.exit_code != 0

# EOF
