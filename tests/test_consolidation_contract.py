"""Migration contracts: ownership, persistence identities and generated apps."""
import ast
import importlib
import json
from pathlib import Path

from django.apps import AppConfig
from scitex_sdk import app, ui, get_frontend_package_dir


def test_runtime_imports_do_not_require_retired_top_level_packages():
    root = get_frontend_package_dir()
    imports = []
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imports.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imports.append((node.module or "").split(".")[0])
    assert not ({"scitex_app", "scitex_ui"} & set(imports))


def test_app_registration_preserves_the_existing_database_label():
    config = AppConfig.create("scitex_sdk.app")
    assert (config.name, config.label) == ("scitex_sdk.app", "scitex_app")


def test_ui_registration_preserves_the_existing_label():
    config = AppConfig.create("scitex_sdk.ui")
    assert (config.name, config.label) == ("scitex_sdk.ui", "scitex_ui")


def test_chat_migration_foreign_key_retains_its_identity():
    migration = importlib.import_module("scitex_sdk.app._chat.migrations.0001_initial")
    fields = dict(migration.Migration.operations[-1].fields)
    assert fields["session"].remote_field.model == "scitex_app.chatsession"


def test_frontend_manifest_and_static_assets_share_one_owner():
    root = get_frontend_package_dir()
    manifest = json.loads((root / "package.json").read_text())
    assert manifest["name"] == "@scitex/sdk" and ui.get_static_dir().is_relative_to(root)


def test_react_scaffold_uses_the_installed_sdk_frontend_and_packed_links(tmp_path):
    from scitex_sdk.app.appmaker import init_app

    init_app(tmp_path, "synthetic_app", frontend_type="react")
    frontend = tmp_path / "synthetic_app/frontend"
    manifest = json.loads((frontend / "package.json").read_text())
    assert (manifest["dependencies"]["@scitex/sdk"], (frontend / ".npmrc").read_text()) == (
        f"file:{get_frontend_package_dir().as_posix()}", "install-links=true\n"
    )
    vite = (frontend / "vite.config.ts").read_text()
    assert "execSync" not in vite and "alias:" not in vite
    assert 'dedupe: ["react", "react-dom"]' in vite


def test_scaffold_emits_canonical_dependencies_and_imports(tmp_path):
    from scitex_sdk.app.appmaker import init_app

    init_app(tmp_path, "synthetic_app")
    metadata = (tmp_path / "pyproject.toml").read_text()
    config = (tmp_path / "synthetic_app/apps.py").read_text()
    assert "scitex-sdk[gui]>=0.3.0" in metadata and "from scitex_sdk.app" in config


def test_generated_python_uses_sdk_contracts_without_host_domain_imports(tmp_path):
    from scitex_sdk.app.appmaker import init_app

    init_app(tmp_path, "synthetic_app")
    imported_roots = set()
    for path in (tmp_path / "synthetic_app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                imported_roots.add((node.module or "").split(".")[0])
    assert not (imported_roots & {"apps", "scitex_hub", "scitex_app", "scitex_ui"})


def test_generated_plugin_runs_the_same_view_at_root_and_under_a_host_mount(tmp_path, monkeypatch):
    import sys
    import re
    import types
    from importlib.metadata import EntryPoint
    from django.test import Client, override_settings
    from django.urls import include, path
    from scitex_sdk.app.appmaker import init_app
    from scitex_sdk.app.plugins import discover_plugin_apps

    name = "sdk_synthetic_app"
    init_app(tmp_path, name, label="SDK Synthetic")
    monkeypatch.syspath_prepend(str(tmp_path))
    metadata = (tmp_path / "pyproject.toml").read_text()
    value = re.search(rf'(?m)^{name} = "([^"]+)"$', metadata).group(1)
    plugin = discover_plugin_apps([EntryPoint(name=name, value=value, group="scitex.apps")])[0]
    urlconf = types.ModuleType("sdk_owned_synthetic_urls")
    urlconf.urlpatterns = [path("", include(f"{name}.urls")), path("mounted/", include(f"{name}.urls"))]
    monkeypatch.setitem(sys.modules, urlconf.__name__, urlconf)
    with override_settings(
        ROOT_URLCONF=urlconf.__name__,
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.app", "scitex_sdk.ui", plugin.app_config],
    ):
        client = Client()
        root = client.get("/")
        mounted = client.get("/mounted/")
        assert (root.status_code, mounted.status_code) == (200, 200)
        assert b'content="/mounted"' in mounted.content and b'content=""' in root.content
