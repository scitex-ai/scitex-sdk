"""The reviewed SDK integration surface remains owned and available on demand."""
import importlib
import json
import subprocess
import sys

import pytest
from scitex_sdk import app, ui


@pytest.mark.parametrize("name", ["i18n", "plugins", "project_context"])
def test_owned_app_integration_module_identity(name):
    assert name in app.__all__
    assert getattr(app, name) is importlib.import_module(f"scitex_sdk.app.{name}")


@pytest.mark.parametrize("name", ["branding", "mount", "project_scope"])
def test_owned_ui_integration_module_identity(name):
    assert name in ui.__all__
    assert getattr(ui, name) is importlib.import_module(f"scitex_sdk.ui.{name}")


@pytest.mark.parametrize("name", ["mount_context", "mount_prefix"])
def test_ui_mount_helper_is_the_existing_ui_function(name):
    assert name in ui.__all__
    assert getattr(ui, name) is getattr(importlib.import_module("scitex_sdk.ui.mount"), name)
    assert ui.mount_prefix is not app.embed.mount_prefix


def test_integration_exports_in_a_cold_process_without_retired_imports():
    code = '''
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
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"owned_integration_exports": 8, "retired_imports": False}
