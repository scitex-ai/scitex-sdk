"""scitex_sdk.app facade tests — identity re-exports from ``scitex_app``."""

from __future__ import annotations

import pytest
import scitex_app
from scitex_sdk import app, ui

# The names the facade re-exports. Kept in sync with scitex_sdk/app.py
# __all__ (minus the facade's own __version__).
_APP_NAMES = [
    "FilesBackend",
    "build_tree",
    "chat",
    "copy_file",
    "delete_file",
    "embed",
    "file_exists",
    "get_files",
    "hosts_to_allow",
    "list_files",
    "paths",
    "read_file",
    "register_backend",
    "rename_file",
    "scaffold",
    "validate",
    "validator",
    "write_file",
]


@pytest.mark.parametrize("name", _APP_NAMES)
def test_app_reexport_matches_source_by_identity(name):
    # Arrange — one re-exported name, picked by parametrize.
    # Act
    facade_obj = getattr(app, name)
    source_obj = getattr(scitex_app, name)
    # Assert
    assert facade_obj is source_obj


def test_facade_declares_matching_version_strings():
    # Arrange — both facade halves plus the expected umbrella version.
    # Act
    observed = (app.__version__, ui.__version__)
    # Assert
    assert observed == ("0.1.0", "0.1.0")
