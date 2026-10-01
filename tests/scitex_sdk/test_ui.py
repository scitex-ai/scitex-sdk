"""Owned UI registry and asset discovery."""
import importlib
import pytest
from scitex_sdk import app, ui, __version__

@pytest.mark.parametrize("name", ["get_component", "get_docs_path", "get_static_dir", "list_components", "register_component"])
def test_ui_public_implementation_is_sdk_owned(name):
    assert getattr(ui, name).__module__.startswith("scitex_sdk.ui")

def test_app_and_ui_are_distinct_owned_modules():
    assert app is not ui

def test_ui_version_has_one_distribution_owner():
    assert ui.__version__ == __version__

def test_owned_static_directory_contains_the_shell():
    assert (ui.get_static_dir() / "css/app.css").is_file()

def test_current_markdown_guidance_is_packaged():
    assert (ui.get_docs_path() / "APP_DEVELOPER_GUIDE.md").is_file()
