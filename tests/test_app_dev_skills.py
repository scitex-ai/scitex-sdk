#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for `scitex-sdk app dev skills` + the legacy top-level alias."""

from __future__ import annotations

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner

from scitex_sdk.app._cli import main


@pytest.fixture
def runner():
    # Arrange
    return CliRunner()


def test_app_dev_skills_help_exit_code_is_zero(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["dev", "skills", "--help"])
    # Assert
    assert result.exit_code == 0


def test_app_dev_skills_lists_bundled_set(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["dev", "skills", "list"])
    # Assert
    assert "01_installation" in result.output


def test_app_legacy_skills_warns_on_stderr(runner):
    # Arrange
    # Act
    result = runner.invoke(main, ["skills", "list"])
    # Assert
    assert "DEPRECATED" in result.stderr


def test_app_legacy_skills_matches_canonical_output(runner):
    # Arrange
    # Act
    legacy = runner.invoke(main, ["skills", "list"])
    canonical = runner.invoke(main, ["dev", "skills", "list"])
    # Assert
    assert canonical.output in legacy.output
