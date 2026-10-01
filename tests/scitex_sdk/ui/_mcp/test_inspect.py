#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_mcp/test_inspect.py

"""Tests for scitex_sdk.ui._mcp.inspect — element-inspection handlers.

The handlers shell out to ``playwright-cli`` via ``subprocess.run``.  Tests
install a real shell shim at ``tmp_path/bin/playwright-cli`` so the suite
exercises the real ``subprocess`` codepath without requiring a real browser.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from scitex_sdk.ui._mcp.inspect import (
    inspect_element_handler,
    inspect_elements_handler,
)


# ---------------------------------------------------------------------------
# Fixture — playwright-cli shell shim
# ---------------------------------------------------------------------------


class _ShimControl:
    """Handle to the playwright-cli shim's response and mode files."""

    def __init__(self, response_file: Path, mode_file: Path) -> None:
        self.response = response_file
        self.mode = mode_file

    def set_response(self, payload: dict | str) -> None:
        """Write the JSON payload the shim should return."""
        inner = json.dumps(payload) if isinstance(payload, dict) else payload
        quoted = json.dumps(inner)
        self.response.write_text(quoted)

    def set_mode(self, mode: str) -> None:
        """Set shim behaviour: ``"normal"`` | ``"sleep"``."""
        self.mode.write_text(mode)


@pytest.fixture
def pw_shim(tmp_path: Path):
    """Install a real ``playwright-cli`` shell shim and prepend it to ``$PATH``.

    The shim reads its canned response from a response file and an optional
    mode file.  This exercises the real ``subprocess.run`` → ``exec`` → shim
    codepath end-to-end, replacing the ``unittest.mock.patch`` that was here
    before.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    response_file = tmp_path / "pw_response.txt"
    mode_file = tmp_path / "pw_mode.txt"
    response_file.write_text("")
    mode_file.write_text("normal")

    shim = bin_dir / "playwright-cli"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f'mode=$(cat "{mode_file}" 2>/dev/null || echo normal)\n'
        'case "$mode" in\n'
        "  sleep) sleep 10; exit 0 ;;\n"
        "  *)\n"
        f'    resp=$(cat "{response_file}")\n'
        '    printf "### Result\\n%s\\n### Ran Playwright code\\n" "$resp"\n'
        "    ;;\n"
        "esac\n"
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    orig_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{orig_path}"
    try:
        yield _ShimControl(response_file, mode_file)
    finally:
        os.environ["PATH"] = orig_path


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_SUCCESS_PAYLOAD = {
    "url": "http://example.com",
    "element": {"tag": "div", "id": "foo", "classes": []},
    "attributes": {},
    "computed": {"display": "block"},
    "inline": "",
    "dimensions": {"width": 100, "height": 50, "top": 0, "left": 0},
    "parentChain": [],
    "matchingRules": [],
}

_ELEMENTS_PAYLOAD = {
    "total": 2,
    "elements": [
        {"index": 0, "tag": "div", "id": None, "classes": "a"},
        {"index": 1, "tag": "div", "id": None, "classes": "a"},
    ],
}


# ---------------------------------------------------------------------------
# inspect_element_handler — happy path
# ---------------------------------------------------------------------------


def test_inspect_element_returns_success_true_on_valid_result(pw_shim):
    # Arrange
    pw_shim.set_response(_SUCCESS_PAYLOAD)
    # Act
    result = inspect_element_handler("#foo")
    # Assert
    assert result["success"] is True


def test_inspect_element_returns_element_tag_from_data(pw_shim):
    # Arrange
    pw_shim.set_response(_SUCCESS_PAYLOAD)
    # Act
    result = inspect_element_handler("#foo")
    # Assert
    assert result["data"]["element"]["tag"] == "div"


# ---------------------------------------------------------------------------
# inspect_element_handler — browser error in data
# ---------------------------------------------------------------------------


def test_inspect_element_reports_success_false_when_browser_returns_error(pw_shim):
    # Arrange
    pw_shim.set_response({"error": "Element not found: #missing"})
    # Act
    result = inspect_element_handler("#missing")
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_error_message_when_element_not_found(pw_shim):
    # Arrange
    pw_shim.set_response({"error": "Element not found: #missing"})
    # Act
    result = inspect_element_handler("#missing")
    # Assert
    assert "Element not found" in result["error"]


# ---------------------------------------------------------------------------
# inspect_element_handler — playwright-cli missing
# ---------------------------------------------------------------------------


def test_inspect_element_reports_success_false_when_cli_missing(tmp_path):
    """No shim installed → subprocess.run raises FileNotFoundError."""
    # Arrange
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    orig_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{orig_path}"
    try:
        # Act
        result = inspect_element_handler("#foo")
    finally:
        os.environ["PATH"] = orig_path
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_playwright_cli_in_error_when_cli_missing(tmp_path):
    """No shim installed → subprocess.run raises FileNotFoundError."""
    # Arrange
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    orig_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{orig_path}"
    try:
        # Act
        result = inspect_element_handler("#foo")
    finally:
        os.environ["PATH"] = orig_path
    # Assert
    assert "playwright-cli" in result["error"]


# ---------------------------------------------------------------------------
# inspect_element_handler — subprocess timeout
# ---------------------------------------------------------------------------


def test_inspect_element_reports_success_false_on_timeout(pw_shim):
    # Arrange
    pw_shim.set_response(_SUCCESS_PAYLOAD)
    pw_shim.set_mode("sleep")
    # Act
    result = inspect_element_handler("#foo", timeout=-4)
    # Assert
    assert result["success"] is False


def test_inspect_element_reports_timed_out_in_error_on_timeout(pw_shim):
    # Arrange
    pw_shim.set_response(_SUCCESS_PAYLOAD)
    pw_shim.set_mode("sleep")
    # Act
    result = inspect_element_handler("#foo", timeout=-4)
    # Assert
    assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# inspect_elements_handler — happy path
# ---------------------------------------------------------------------------


def test_inspect_elements_returns_success_true_on_valid_result(pw_shim):
    # Arrange
    pw_shim.set_response(_ELEMENTS_PAYLOAD)
    # Act
    result = inspect_elements_handler(".a", limit=5)
    # Assert
    assert result["success"] is True


def test_inspect_elements_returns_selector_from_input(pw_shim):
    # Arrange
    pw_shim.set_response(_ELEMENTS_PAYLOAD)
    # Act
    result = inspect_elements_handler(".a", limit=5)
    # Assert
    assert result["selector"] == ".a"


def test_inspect_elements_returns_total_count(pw_shim):
    # Arrange
    pw_shim.set_response(_ELEMENTS_PAYLOAD)
    # Act
    result = inspect_elements_handler(".a", limit=5)
    # Assert
    assert result["total"] == 2


def test_inspect_elements_returns_correct_elements_length(pw_shim):
    # Arrange
    pw_shim.set_response(_ELEMENTS_PAYLOAD)
    # Act
    result = inspect_elements_handler(".a", limit=5)
    # Assert
    assert len(result["elements"]) == 2


# ---------------------------------------------------------------------------
# inspect_elements_handler — playwright-cli missing
# ---------------------------------------------------------------------------


def test_inspect_elements_reports_success_false_when_cli_missing(tmp_path):
    """No shim installed → subprocess.run raises FileNotFoundError."""
    # Arrange
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    orig_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{orig_path}"
    try:
        # Act
        result = inspect_elements_handler(".a")
    finally:
        os.environ["PATH"] = orig_path
    # Assert
    assert result["success"] is False


def test_inspect_elements_reports_playwright_cli_in_error_when_cli_missing(tmp_path):
    """No shim installed → subprocess.run raises FileNotFoundError."""
    # Arrange
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    orig_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{orig_path}"
    try:
        # Act
        result = inspect_elements_handler(".a")
    finally:
        os.environ["PATH"] = orig_path
    # Assert
    assert "playwright-cli" in result["error"]


# EOF
