"""scitex_sdk.ui facade tests — identity re-exports from ``scitex_ui``."""

from __future__ import annotations

import pytest
import scitex_ui
from scitex_sdk import app, ui

# The names the facade re-exports. Kept in sync with scitex_sdk/ui.py
# __all__ (minus the facade's own __version__).
_UI_NAMES = [
    "get_component",
    "get_docs_path",
    "get_static_dir",
    "list_components",
    "register_component",
]


@pytest.mark.parametrize("name", _UI_NAMES)
def test_ui_reexport_matches_source_by_identity(name):
    # Arrange — one re-exported name, picked by parametrize.
    # Act
    facade_obj = getattr(ui, name)
    source_obj = getattr(scitex_ui, name)
    # Assert
    assert facade_obj is source_obj


def test_app_and_ui_facades_are_distinct_modules():
    # Arrange — the two facade halves must never alias each other.
    # Act
    same = app is ui
    # Assert
    assert not same
