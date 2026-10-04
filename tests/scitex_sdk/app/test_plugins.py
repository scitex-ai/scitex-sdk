#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The one-line plugin contract: a ``scitex.apps`` entry point makes a hub app.

Mirrors src/scitex_sdk/app/plugins.py (PS-204). Real ``EntryPoint`` objects, no mocks.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from types import SimpleNamespace

from scitex_sdk.app.plugins import (
    ENTRY_POINT_GROUP,
    PluginApp,
    app_config_path,
    app_module_of,
    discover_plugin_apps,
    installed_app_paths,
    mount_route,
)


def _ep(name, value):
    return EntryPoint(name=name, value=value, group=ENTRY_POINT_GROUP)


def test_entry_point_value_becomes_installed_apps_path():
    # Arrange
    value = "figrecipe._django.apps:FigRecipeEditorConfig"
    # Act
    path = app_config_path(value)
    # Assert
    assert path == "figrecipe._django.apps.FigRecipeEditorConfig"


def test_bare_and_appconfig_entries_name_the_same_app_module():
    # Arrange
    entries = ["figrecipe._django", "figrecipe._django.apps.FigRecipeEditorConfig"]
    # Act
    modules = {app_module_of(e) for e in entries}
    # Assert
    assert modules == {"figrecipe._django"}


def test_discovery_is_sorted_and_first_name_wins():
    # Arrange
    eps = [_ep("b", "b.apps:B"), _ep("a", "a.apps:A"), _ep("a", "other.apps:X")]
    # Act
    found = discover_plugin_apps(eps)
    # Assert
    assert [p.app_config for p in found] == ["a.apps.A", "b.apps.B"]


def test_plugin_replaces_hand_written_entry_in_place():
    # Arrange
    existing = ["scitex_ui", "figrecipe._django", "scitex_writer._django.apps.W"]
    plugins = [PluginApp("figrecipe", "figrecipe._django.apps.FigRecipeEditorConfig")]
    # Act
    merged = installed_app_paths(existing, plugins)
    # Assert
    assert merged == [
        "scitex_ui",
        "figrecipe._django.apps.FigRecipeEditorConfig",
        "scitex_writer._django.apps.W",
    ]


def test_new_plugin_is_appended():
    # Arrange
    plugins = [PluginApp("hello", "hello_world.apps.HelloWorldConfig")]
    # Act
    merged = installed_app_paths(["scitex_ui"], plugins)
    # Assert
    assert merged == ["scitex_ui", "hello_world.apps.HelloWorldConfig"]


def test_mount_route_defaults_to_apps_slug():
    # Arrange
    config = SimpleNamespace(label="hello_world", manifest={"slug": "hello-world"})
    # Act
    route = mount_route(config)
    # Assert
    assert route == "apps/hello-world/"


def test_mount_route_honours_manifest_url():
    # Arrange
    config = SimpleNamespace(label="x", manifest={"slug": "x", "url": "/apps/u/x/"})
    # Act
    route = mount_route(config)
    # Assert
    assert route == "apps/u/x/"


def _leaf_module(tmp_path, name, body):
    # Arrange
    (tmp_path / f"{name}.py").write_text(body, encoding="utf-8")
    # Act
    import sys
    sys.path.insert(0, str(tmp_path))
    # Assert
    return name


def _unpath(tmp_path):
    # Arrange
    import sys
    # Act
    sys.path.remove(str(tmp_path))
    # Assert
    assert True


def test_leaf_declarations_reads_existing_exports(tmp_path):
    # Arrange
    from collections.abc import Callable

    from scitex_sdk.app.plugins import leaf_declarations
    mod = _leaf_module(tmp_path, "leaf_a", "def context_builder(r): return {}\npartial_template = 'leaf/page.html'\n")
    try:
        # Act
        found = leaf_declarations(mod, {"context_builder": Callable, "partial_template": str, "missing": str})
    finally:
        _unpath(tmp_path)
    # Assert
    assert sorted(found) == ["context_builder", "partial_template"]


def test_leaf_declarations_absent_module_yields_empty():
    # Arrange
    from scitex_sdk.app.plugins import leaf_declarations
    # Act
    found = leaf_declarations("no_such_leaf_module_xyz", {"context_builder": object})
    # Assert
    assert found == {}


def test_leaf_declarations_wrong_type_refused(tmp_path):
    # Arrange
    import pytest

    from scitex_sdk.app.plugins import LeafContractError, leaf_declarations
    mod = _leaf_module(tmp_path, "leaf_b", "partial_template = 42\n")
    try:
        # Act
        # Assert
        with pytest.raises(LeafContractError, match="leaf_b.partial_template"):
            leaf_declarations(mod, {"partial_template": str})
    finally:
        _unpath(tmp_path)


def test_discovery_values_stay_load_compatible():
    # Arrange — EntryPoint.load only parses single-config values: no smuggling.
    eps = [_ep("fig", "fig._django.apps:FigRecipeEditorConfig")]
    # Act
    found = discover_plugin_apps(eps)
    # Assert
    assert " " not in found[0].app_config and "\t" not in found[0].app_config


def test_companions_appended_unless_listed():
    # Arrange
    plugins = [PluginApp("fig", "figrecipe._django.apps.FigRecipeEditorConfig")]
    companions = (
        "figrecipe._django",
        "figrecipe._django.apps.ScitexAppChatConfig",
    )
    # Act
    merged = installed_app_paths([], plugins, companions)
    # Assert
    assert merged == [
        "figrecipe._django.apps.FigRecipeEditorConfig",
        "figrecipe._django",
        "figrecipe._django.apps.ScitexAppChatConfig",
    ]


def test_undeclared_same_module_entry_still_replaced():
    # Arrange — without an explicit companion declaration the 0.3.2 primary
    # same-module replacement rule applies unchanged.
    plugins = [PluginApp("fig", "figrecipe._django.apps.FigRecipeEditorConfig")]
    # Act
    merged = installed_app_paths(["figrecipe._django.apps.ScitexAppChatConfig"], plugins)
    # Assert
    assert merged == ["figrecipe._django.apps.FigRecipeEditorConfig"]


def test_declared_companion_survives_primary_replacement():
    # Arrange — an explicitly declared companion is exempt from primary
    # same-module replacement: both entries persist, no silent drop.
    plugins = [PluginApp("fig", "figrecipe._django.apps.FigRecipeEditorConfig")]
    companions = ("figrecipe._django.apps.ScitexAppChatConfig",)
    # Act
    merged = installed_app_paths(
        ["figrecipe._django.apps.ScitexAppChatConfig"], plugins, companions
    )
    # Assert
    assert merged == [
        "figrecipe._django.apps.ScitexAppChatConfig",
        "figrecipe._django.apps.FigRecipeEditorConfig",
    ]
