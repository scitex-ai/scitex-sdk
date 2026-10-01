"""The reviewed SDK integration surface remains owned and available on demand."""
import importlib
import json
import subprocess
import sys

import pytest

from scitex_sdk import app, ui


@pytest.mark.parametrize("name", ["i18n", "plugins", "project_context"])
def test_owned_app_integration_module_is_advertised(name):
    # Arrange
    owner = app
    # Act
    exports = owner.__all__
    # Assert
    assert name in exports


@pytest.mark.parametrize("name", ["i18n", "plugins", "project_context"])
def test_owned_app_integration_module_identity(name):
    # Arrange
    expected_module = f"scitex_sdk.app.{name}"
    # Act
    value = getattr(app, name)
    # Assert
    assert value is importlib.import_module(expected_module)


@pytest.mark.parametrize("name", ["branding", "mount", "project_scope"])
def test_owned_ui_integration_module_is_advertised(name):
    # Arrange
    owner = ui
    # Act
    exports = owner.__all__
    # Assert
    assert name in exports


@pytest.mark.parametrize("name", ["branding", "mount", "project_scope"])
def test_owned_ui_integration_module_identity(name):
    # Arrange
    expected_module = f"scitex_sdk.ui.{name}"
    # Act
    value = getattr(ui, name)
    # Assert
    assert value is importlib.import_module(expected_module)


@pytest.mark.parametrize("name", ["mount_context", "mount_prefix"])
def test_ui_mount_helper_is_advertised(name):
    # Arrange
    owner = ui
    # Act
    exports = owner.__all__
    # Assert
    assert name in exports


@pytest.mark.parametrize("name", ["mount_context", "mount_prefix"])
def test_ui_mount_helper_is_the_existing_ui_function(name):
    # Arrange
    expected_module = "scitex_sdk.ui.mount"
    # Act
    value = getattr(ui, name)
    # Assert
    assert value is getattr(importlib.import_module(expected_module), name)


def test_ui_mount_prefix_remains_distinct_from_the_app_mount_prefix():
    # Arrange
    app_prefix = app.embed.mount_prefix
    # Act
    ui_prefix = ui.mount_prefix
    # Assert
    assert ui_prefix is not app_prefix


def _cold_exports():
    code = """
import importlib, importlib.abc, json, sys
class RetiredImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'scitex_app', 'scitex_ui'}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, RetiredImports())
from scitex_sdk import app, ui
for parent, names in [(app, ['i18n', 'plugins', 'project_context']),
                       (ui, ['branding', 'mount', 'project_scope'])]:
    for name in names:
        assert getattr(parent, name) is importlib.import_module(parent.__name__ + '.' + name)
for name in ['mount_context', 'mount_prefix']:
    assert getattr(ui, name) is getattr(importlib.import_module('scitex_sdk.ui.mount'), name)
assert not any(name.split('.')[0] in {'scitex_app', 'scitex_ui'} for name in sys.modules)
print(json.dumps({'owned_integration_exports': 8, 'retired_imports': False}))
"""
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)


def test_integration_exports_exit_cleanly_in_a_cold_process_without_retired_imports():
    # Arrange
    run = _cold_exports
    # Act
    result = run()
    # Assert
    assert result.returncode == 0, result.stderr


def test_integration_exports_report_owned_identities_as_json_in_a_cold_process():
    # Arrange
    run = _cold_exports
    # Act
    result = run()
    payload = json.loads(result.stdout)
    # Assert
    assert payload == {"owned_integration_exports": 8, "retired_imports": False}
