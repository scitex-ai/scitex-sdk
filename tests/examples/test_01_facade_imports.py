"""Smoke test for examples/01_facade_imports.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "01_facade_imports.py"


def test_example_file_exists_on_disk():
    # Arrange
    expected_path = EXAMPLE
    # Act
    found = expected_path.exists()
    # Assert
    assert found, f"missing example file: {expected_path}"


def test_example_spec_has_resolvable_loader():
    # Arrange
    target = EXAMPLE
    # Act
    spec = importlib.util.spec_from_file_location("ex", target)
    # Assert
    assert spec is not None and spec.loader is not None


def test_example_module_object_creates_from_spec():
    # Arrange
    spec = importlib.util.spec_from_file_location("ex", EXAMPLE)
    # Act
    module = importlib.util.module_from_spec(spec)
    # Assert
    assert module is not None


def test_example_runs_successfully_as_a_script():
    # Arrange — run the example end-to-end in a fresh interpreter.
    target = str(EXAMPLE)
    # Act
    proc = subprocess.run(
        [sys.executable, target], capture_output=True, text=True, check=False
    )
    # Assert
    assert proc.returncode == 0, proc.stderr
