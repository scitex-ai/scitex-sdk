"""Required runtime imports must resolve; SDK App/UI are not external peers."""
import importlib
import pytest

CROSS_PACKAGE_IMPORTS = [
    "scitex_config._ecosystem",
    "scitex_dev._cli._completion",
    "scitex_dev.cli",
    "scitex_dev.ecosystem",
    "scitex_dev.linter._rules._base",
    "scitex_dev.linter.spi",
    "scitex_dev.project",
    "scitex_logging",
]

@pytest.mark.parametrize("module_name", CROSS_PACKAGE_IMPORTS)
def test_required_runtime_dependency_import(module_name):
    # Arrange
    name = module_name
    # Act
    module = importlib.import_module(name)
    # Assert
    assert module.__name__ == module_name
