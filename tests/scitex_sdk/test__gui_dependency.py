"""GUI imports explain absent Django and preserve broken-peer failures."""

import json
import subprocess
import sys

import pytest

_MODULES = [
    "scitex_sdk.creator.urls", "scitex_sdk.creator.views",
    "scitex_sdk.ui.context_processors", "scitex_sdk.ui.middleware",
    "scitex_sdk.ui.templatetags.scitex_help",
    "scitex_sdk.ui.templatetags.scitex_i18n",
    "scitex_sdk.ui.templatetags.scitex_panes",
    "scitex_sdk.ui.templatetags.scitex_project_picker",
    "scitex_sdk.ui.templatetags.scitex_static", "scitex_sdk.urls",
]
_CALLS = [
    ("scitex_sdk.host", "module._provider('SCITEX_PROJECT_STORAGE')"),
    ("scitex_sdk.host", "module.authenticated_user(SimpleNamespace(user=None))"),
    ("scitex_sdk.host", "module.project_access(SimpleNamespace(user=None))"),
    ("scitex_sdk.local", "module._root()"),
    ("scitex_sdk.local", "module.LocalProjectStore().store_access('owned', None)"),
    ("scitex_sdk.ui.i18n", "module.js_catalog('scitex_sdk.ui', language='en')"),
    ("scitex_sdk.ui.project_scope", "module.host_project_provider()"),
    ("scitex_sdk.ui.project_scope", "module.host_project_provider_url()"),
    ("scitex_sdk.ui.project_scope", "module.project_listing_view(None)"),
    ("scitex_sdk.ui.project_scope", "module.scoped_project_listing_view(None)"),
]
_CASES = [(module, "None") for module in _MODULES] + _CALLS


@pytest.mark.parametrize(("module", "operation"), _CASES)
@pytest.mark.parametrize("missing", ["django", "owned_missing_django_peer"])
def test_gui_dependency_failure(module, operation, missing):
    # Arrange: fail an actual import, before settings, providers or network use.
    code = '''
import importlib, importlib.abc, json, sys
from types import SimpleNamespace
class MissingDependency(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "django":
            raise ModuleNotFoundError("owned missing dependency", name=sys.argv[3])
sys.meta_path.insert(0, MissingDependency())
try:
    module = importlib.import_module(sys.argv[1])
    if sys.argv[2] != "None":
        assert "django" not in sys.modules
        operations = {
            "module._provider('SCITEX_PROJECT_STORAGE')": lambda: module._provider('SCITEX_PROJECT_STORAGE'),
            "module.authenticated_user(SimpleNamespace(user=None))": lambda: module.authenticated_user(SimpleNamespace(user=None)),
            "module.project_access(SimpleNamespace(user=None))": lambda: module.project_access(SimpleNamespace(user=None)),
            "module._root()": lambda: module._root(),
            "module.LocalProjectStore().store_access('owned', None)": lambda: module.LocalProjectStore().store_access('owned', None),
            "module.js_catalog('scitex_sdk.ui', language='en')": lambda: module.js_catalog('scitex_sdk.ui', language='en'),
            "module.host_project_provider()": lambda: module.host_project_provider(),
            "module.host_project_provider_url()": lambda: module.host_project_provider_url(),
            "module.project_listing_view(None)": lambda: module.project_listing_view(None),
            "module.scoped_project_listing_view(None)": lambda: module.scoped_project_listing_view(None),
        }
        operations[sys.argv[2]]()
except ImportError as error:
    print(json.dumps({"type": type(error).__name__, "message": str(error),
                      "name": getattr(error, "name", None),
                      "cause_name": getattr(error.__cause__, "name", None)}))
else:
    raise AssertionError("the dependency failure must stay visible")
'''
    # Act
    result = subprocess.run(
        [sys.executable, "-c", code, module, operation, missing],
        capture_output=True, text=True, timeout=10, check=True,
    )
    observed = json.loads(result.stdout)
    # Assert
    if missing == "django":
        assert observed["type"] == "ImportError"
        assert "pip install 'scitex-sdk[gui]'" in observed["message"]
        assert observed["cause_name"] == "django"
    else:
        assert observed == {
            "type": "ModuleNotFoundError", "message": "owned missing dependency",
            "name": missing, "cause_name": None,
        }
