"""Required runtime imports must resolve; SDK App/UI are not external peers."""
import importlib
import pytest

CROSS_PACKAGE_IMPORTS = ["scitex_config", "scitex_logging"]

@pytest.mark.parametrize("module_name", CROSS_PACKAGE_IMPORTS)
def test_required_runtime_dependency_import(module_name):
    assert importlib.import_module(module_name).__name__ == module_name
