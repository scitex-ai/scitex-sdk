#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_sdk.creator — starters, pure helpers, and the manifest.

One assert per test. No mocks: the create path below scaffolds into a
real tmp dir through the real engine.
"""

from __future__ import annotations

import json
from pathlib import Path

from scitex_sdk import creator
from scitex_sdk.creator import (
    DEFAULT_STARTER,
    STARTERS,
    STARTERS_BY_KEY,
    app_module_name,
    target_slug,
    validate_create_input,
)

_MANIFEST = Path(creator.__file__).resolve().parent / "manifest.json"


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def test_starter_keys_match_the_hub_contract():
    # Arrange
    # Act
    keys = {s.key for s in STARTERS}
    # Assert
    assert keys == {
        "data_entry",
        "dashboard",
        "log_viewer",
        "blank",
    }


def test_default_starter_is_blank():
    # Arrange
    # Act
    starter = DEFAULT_STARTER
    # Assert
    assert starter == "blank"


def test_default_starter_is_a_known_starter():
    # Arrange
    # Act
    known = DEFAULT_STARTER in STARTERS_BY_KEY
    # Assert
    assert known


def test_app_module_name_appends_suffix():
    # Arrange
    # Act
    module = app_module_name("my-cool-thing")
    # Assert
    assert module == "my_cool_thing_app"


def test_app_module_name_keeps_suffix():
    # Arrange
    # Act
    module = app_module_name("demo_app")
    # Assert
    assert module == "demo_app"


def test_target_slug_derives_dirname():
    # Arrange
    # Act
    slug = target_slug("My Cool App!")
    # Assert
    assert slug == "my-cool-app"


def test_validate_create_input_accepts_good_input():
    # Arrange
    # Act
    errors = validate_create_input("My App", "does things", "blank")
    # Assert
    assert errors == []


def test_validate_create_input_rejects_empty_label():
    # Arrange
    # Act
    errors = validate_create_input("  ", "does things", "blank")
    # Assert
    assert errors != []


def test_validate_create_input_rejects_unknown_starter():
    # Arrange
    # Act
    errors = validate_create_input("My App", "does things", "nope")
    # Assert
    assert errors != []


def test_manifest_declares_required_keys():
    # Arrange
    # Act
    manifest = _manifest()
    # Assert
    assert {"name", "slug", "label", "pip_package", "icon", "license"} <= set(
        manifest
    )


def test_manifest_declares_no_version_key():
    # Arrange
    # Act
    manifest = _manifest()
    # Assert
    assert "version" not in manifest


def test_manifest_standalone_port_is_31301():
    # Arrange
    # Act
    manifest = _manifest()
    # Assert
    assert manifest["standalone_port"] == 31301


def test_manifest_standalone_command_is_sdk_gui_serve():
    # Arrange
    # Act
    manifest = _manifest()
    # Assert
    assert manifest["standalone_command"] == "scitex-sdk gui serve"

# EOF
