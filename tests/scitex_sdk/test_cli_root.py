#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the top-level `scitex-sdk` command surface (ecosystem §1a/§2/§4/§6b).

One assert per test. No mocks: CliRunner drives the real command tree.
"""

from __future__ import annotations

import json

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner

from scitex_sdk.cli import main


@pytest.fixture
def runner():
    # Arrange
    return CliRunner()


def test_root_help_shows_version_line(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["--help"])
    # Assert
    assert "scitex-sdk (v" in result.output


def test_root_help_documents_config_fallback(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["--help"])
    # Assert
    assert "config.yaml" in result.output


def test_root_help_recursive_lists_subcommands(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["--help-recursive"])
    # Assert
    assert "=== scitex-sdk mcp ===" in result.output


def test_root_has_list_python_apis(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["list-python-apis", "--help"])
    # Assert
    assert result.exit_code == 0


def test_root_list_python_apis_covers_both_components(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["list-python-apis", "--json"])
    # Assert
    assert {"app", "ui"} <= {row["component"] for row in json.loads(result.output)}


def test_root_has_mcp_list_tools(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["mcp", "list-tools", "--json"])
    # Assert
    assert result.exit_code == 0


def test_root_mcp_list_tools_covers_both_servers(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["mcp", "list-tools", "--json"])
    # Assert
    assert {"app", "ui"} <= {row["server"] for row in json.loads(result.output)}


def test_root_has_skills_group(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["skills", "--help"])
    # Assert
    assert result.exit_code == 0


def test_root_has_docs_group(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["docs", "--help"])
    # Assert
    assert result.exit_code == 0
