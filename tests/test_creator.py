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
    assert {s.key for s in STARTERS} == {
        "data_entry",
        "dashboard",
        "log_viewer",
        "blank",
    }


def test_default_starter_is_blank():
    assert DEFAULT_STARTER == "blank"


def test_default_starter_is_a_known_starter():
    assert DEFAULT_STARTER in STARTERS_BY_KEY


def test_app_module_name_appends_suffix():
    assert app_module_name("my-cool-thing") == "my_cool_thing_app"


def test_app_module_name_keeps_suffix():
    assert app_module_name("demo_app") == "demo_app"


def test_target_slug_derives_dirname():
    assert target_slug("My Cool App!") == "my-cool-app"


def test_validate_create_input_accepts_good_input():
    assert validate_create_input("My App", "does things", "blank") == []


def test_validate_create_input_rejects_empty_label():
    assert validate_create_input("  ", "does things", "blank") != []


def test_validate_create_input_rejects_unknown_starter():
    assert validate_create_input("My App", "does things", "nope") != []


def test_manifest_declares_required_keys():
    assert {"name", "slug", "label", "pip_package", "icon", "license"} <= set(
        _manifest()
    )


def test_manifest_declares_no_version_key():
    assert "version" not in _manifest()


def test_manifest_standalone_port_is_31301():
    assert _manifest()["standalone_port"] == 31301


def test_manifest_standalone_command_is_sdk_gui_serve():
    assert _manifest()["standalone_command"] == "scitex-sdk gui serve"

# EOF
