"""The SDK owns the former App public API and physical submodules."""
import importlib
import types
import pytest
from scitex_sdk import app, __version__

NAMES = ["FilesBackend", "build_tree", "chat", "copy_file", "delete_file",
         "embed", "file_exists", "get_files", "hosts_to_allow", "list_files",
         "paths", "read_file", "register_backend", "rename_file", "scaffold",
         "validate", "validator", "write_file"]

@pytest.mark.parametrize("name", NAMES)
def test_app_public_implementation_is_sdk_owned(name):
    obj = getattr(app, name)
    owner = obj.__name__ if isinstance(obj, types.ModuleType) else obj.__module__
    assert owner.startswith("scitex_sdk.app")

def test_app_version_has_one_distribution_owner():
    assert app.__version__ == __version__

@pytest.mark.parametrize("name", ["embed", "sdk", "_django", "appmaker", "paths"])
def test_app_submodules_are_physical_canonical_imports(name):
    assert importlib.import_module(f"scitex_sdk.app.{name}").__name__ == f"scitex_sdk.app.{name}"
