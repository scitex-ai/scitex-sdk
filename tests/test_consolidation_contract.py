"""Migration contracts: ownership, persistence identities and generated apps."""
import ast
import importlib
import json
import re
import sys
import types
from importlib.metadata import EntryPoint
from uuid import uuid4

import pytest
from django.apps import AppConfig
from django.test import Client, override_settings
from django.urls import include, path

from scitex_sdk import get_frontend_package_dir, ui
from scitex_sdk.app.appmaker import init_app
from scitex_sdk.app.plugins import discover_plugin_apps


@pytest.fixture
def react_frontend(tmp_path):
    init_app(tmp_path, "synthetic_app", frontend_type="react")
    return tmp_path / "synthetic_app/frontend"


@pytest.fixture
def generated_app(tmp_path):
    init_app(tmp_path, "synthetic_app")
    return tmp_path


@pytest.fixture
def generated_plugin_client(tmp_path, monkeypatch):
    name = f"sdk_synthetic_app_{uuid4().hex}"
    init_app(tmp_path, name, label="SDK Synthetic")
    monkeypatch.syspath_prepend(str(tmp_path))
    metadata = (tmp_path / "pyproject.toml").read_text()
    value = re.search(rf'(?m)^{name} = "([^"]+)"$', metadata).group(1)
    plugin = discover_plugin_apps([
        EntryPoint(name=name, value=value, group="scitex.apps")
    ])[0]
    urlconf = types.ModuleType(f"sdk_owned_synthetic_urls_{uuid4().hex}")
    urlconf.urlpatterns = [
        path("", include(f"{name}.urls")),
        path("mounted/", include(f"{name}.urls")),
    ]
    monkeypatch.setitem(sys.modules, urlconf.__name__, urlconf)
    with override_settings(
        ROOT_URLCONF=urlconf.__name__,
        INSTALLED_APPS=[
            "django.contrib.staticfiles", "scitex_sdk.app", "scitex_sdk.ui",
            plugin.app_config,
        ],
    ):
        yield Client()


def test_runtime_imports_do_not_require_retired_top_level_packages():
    # Arrange
    root = get_frontend_package_dir()
    imports = []
    # Act
    for source in root.rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Import):
                imports.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imports.append((node.module or "").split(".")[0])
    # Assert
    assert not ({"scitex_app", "scitex_ui"} & set(imports))


@pytest.mark.parametrize("component", ["app", "ui"])
def test_component_registration_uses_its_sdk_python_name(component):
    # Arrange
    expected = f"scitex_sdk.{component}"
    # Act
    config = AppConfig.create(expected)
    # Assert
    assert config.name == expected


@pytest.mark.parametrize("component", ["app", "ui"])
def test_component_registration_preserves_its_existing_database_label(component):
    # Arrange
    expected = f"scitex_{component}"
    # Act
    config = AppConfig.create(f"scitex_sdk.{component}")
    # Assert
    assert config.label == expected


def test_chat_migration_foreign_key_retains_its_identity():
    # Arrange
    name = "scitex_sdk.app._chat.migrations.0001_initial"
    # Act
    migration = importlib.import_module(name)
    fields = dict(migration.Migration.operations[-1].fields)
    # Assert
    assert fields["session"].remote_field.model == "scitex_app.chatsession"


def test_frontend_manifest_names_the_sdk_owner():
    # Arrange
    root = get_frontend_package_dir()
    # Act
    manifest = json.loads((root / "package.json").read_text())
    # Assert
    assert manifest["name"] == "@scitex/sdk"


def test_static_assets_belong_to_the_frontend_owner():
    # Arrange
    root = get_frontend_package_dir()
    # Act
    directory = ui.get_static_dir()
    # Assert
    assert directory.is_relative_to(root)


def test_react_scaffold_uses_the_installed_sdk_frontend(react_frontend):
    # Arrange
    expected = f"file:{get_frontend_package_dir().as_posix()}"
    # Act
    manifest = json.loads((react_frontend / "package.json").read_text())
    # Assert
    assert manifest["dependencies"]["@scitex/sdk"] == expected


def test_react_scaffold_packs_file_dependencies(react_frontend):
    # Arrange
    config = react_frontend / ".npmrc"
    # Act
    contents = config.read_text()
    # Assert
    assert contents == "install-links=true\n"


@pytest.mark.parametrize("forbidden", ["execSync", "alias:"])
def test_react_scaffold_has_no_environment_resolution_workaround(react_frontend, forbidden):
    # Arrange
    config = react_frontend / "vite.config.ts"
    # Act
    contents = config.read_text()
    # Assert
    assert forbidden not in contents


def test_react_scaffold_deduplicates_react_peers(react_frontend):
    # Arrange
    config = react_frontend / "vite.config.ts"
    # Act
    contents = config.read_text()
    # Assert
    assert 'dedupe: ["react", "react-dom"]' in contents


def test_scaffold_emits_the_canonical_gui_dependency(generated_app):
    # Arrange
    config = generated_app / "pyproject.toml"
    # Act
    metadata = config.read_text()
    # Assert
    assert "scitex-sdk[gui]>=0.3.0" in metadata


def test_scaffold_imports_the_sdk_app_config(generated_app):
    # Arrange
    config = generated_app / "synthetic_app/apps.py"
    # Act
    contents = config.read_text()
    # Assert
    assert "from scitex_sdk.app" in contents


def test_generated_python_uses_sdk_contracts_without_host_domain_imports(generated_app):
    # Arrange
    imported_roots = set()
    # Act
    for source in (generated_app / "synthetic_app").rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                imported_roots.add((node.module or "").split(".")[0])
    # Assert
    assert not (imported_roots & {"apps", "scitex_hub", "scitex_app", "scitex_ui"})


@pytest.mark.parametrize("url", ["/", "/mounted/"])
def test_generated_plugin_view_succeeds_standalone_and_mounted(generated_plugin_client, url):
    # Arrange
    client = generated_plugin_client
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("url,marker", [
    ("/", b'content=""'),
    ("/mounted/", b'content="/mounted"'),
])
def test_generated_plugin_view_reports_its_actual_mount(generated_plugin_client, url, marker):
    # Arrange
    client = generated_plugin_client
    # Act
    response = client.get(url)
    # Assert
    assert marker in response.content


def test_static_directory_and_frontend_owner_agree_through_a_symlink(tmp_path, monkeypatch):
    # Arrange
    root = get_frontend_package_dir()
    alias = tmp_path / "sdk-alias"
    alias.symlink_to(root, target_is_directory=True)
    monkeypatch.setattr(ui, "__file__", str(alias / "ui/__init__.py"))
    # Act
    directory = ui.get_static_dir()
    # Assert
    assert directory == root / "ui/static/scitex_sdk/ui"
