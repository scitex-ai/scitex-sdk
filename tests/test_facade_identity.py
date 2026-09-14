"""Facade identity tests — the contract that makes the import rewrite safe.

Every name re-exported by ``scitex_sdk.app`` / ``scitex_sdk.ui`` must be the
SAME object (identity) as the corresponding name in ``scitex_app`` /
``scitex_ui``. That is what lets a consumer rewrite
``from scitex_app import X`` -> ``from scitex_sdk.app import X`` mechanically
with zero behavior change. A copy or a reimplementation would break this.
"""

from __future__ import annotations

import scitex_app
import scitex_ui
from scitex_sdk import app, ui


def _assert_identity(facade_module, source_module, name):
    assert getattr(facade_module, name) is getattr(source_module, name), (
        f"scitex_sdk facade re-export {name!r} is not identical to "
        f"{source_module.__name__}.{name}"
    )


# The names the facade re-exports. Kept in sync with scitex_sdk/app.py and
# scitex_sdk/ui.py __all__ (minus the facade's own __version__).
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
_UI_NAMES = [
    "get_component",
    "get_docs_path",
    "get_static_dir",
    "list_components",
    "register_component",
]


def test_app_facade_reexports_by_identity():
    for name in _APP_NAMES:
        _assert_identity(app, scitex_app, name)


def test_ui_facade_reexports_by_identity():
    for name in _UI_NAMES:
        _assert_identity(ui, scitex_ui, name)


def test_facade_modules_are_distinct_from_each_other():
    assert app is not ui


def test_facade_carries_its_own_version_string():
    # The facade declares its own version; it must be a real version string.
    assert app.__version__ == ui.__version__ == "0.1.0"
