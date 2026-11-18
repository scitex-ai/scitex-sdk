"""Optional GUI registration reports absent Django without masking broken peers."""

import json
import subprocess
import sys

import pytest

_MODULES = ["scitex_sdk.app.apps", "scitex_sdk.app._chat.apps", "scitex_sdk.ui.apps"]


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("missing", ["django", "owned_missing_django_peer"])
def test_django_registration_dependency_errors(module, missing):
    # Arrange: fail the real import boundary before Django configures anything.
    code = '''
import importlib, importlib.abc, json, sys
class MissingDependency(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "django":
            raise ModuleNotFoundError("owned missing dependency", name=sys.argv[2])
sys.meta_path.insert(0, MissingDependency())
try:
    importlib.import_module(sys.argv[1])
except ImportError as error:
    print(json.dumps({"type": type(error).__name__, "message": str(error),
                      "name": getattr(error, "name", None),
                      "cause_name": getattr(error.__cause__, "name", None)}))
else:
    raise AssertionError("the dependency failure must remain visible")
'''
    # Act
    result = subprocess.run(
        [sys.executable, "-c", code, module, missing],
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
