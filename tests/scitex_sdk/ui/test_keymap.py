#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_sdk/ui/test_keymap.py
"""Guards for the Django keymap integration hook (scitex_sdk.ui.keymap).

Each test function carries exactly one assertion and the AAA markers the
repo's test-quality gate (PA-307 STX-TQ002/007) requires.
"""

from __future__ import annotations

import json
import re

import pytest

from scitex_sdk.ui.keymap import (
    KEYMAP_GLOBAL_DEFAULTS,
    keymap_defaults,
    render_keymap_init,
)


def _payload(script_tag: str) -> dict:
    """Extract the JSON body from a rendered <script> tag."""
    m = re.search(r'<script[^>]*>(.*?)</script>', script_tag, re.DOTALL)
    assert m is not None, "could not extract script body"
    return json.loads(m.group(1))


class TestGlobalDefaults:
    """The default command set is the migration source from keyboard-shortcuts."""

    @pytest.mark.parametrize("cmd_id", sorted(KEYMAP_GLOBAL_DEFAULTS))
    def test_every_default_has_a_label(self, cmd_id: str) -> None:
        # Arrange
        spec = KEYMAP_GLOBAL_DEFAULTS[cmd_id]
        # Act
        label = spec.get("label")
        # Assert
        assert isinstance(label, str) and label != "", f"{cmd_id} missing label"

    @pytest.mark.parametrize("cmd_id", sorted(KEYMAP_GLOBAL_DEFAULTS))
    def test_every_default_has_a_group(self, cmd_id: str) -> None:
        # Arrange
        spec = KEYMAP_GLOBAL_DEFAULTS[cmd_id]
        # Act
        group = spec.get("group")
        # Assert
        assert isinstance(group, str) and group != "", f"{cmd_id} missing group"

    @pytest.mark.parametrize("cmd_id", sorted(KEYMAP_GLOBAL_DEFAULTS))
    def test_every_default_has_a_non_empty_sequence(self, cmd_id: str) -> None:
        # Arrange
        spec = KEYMAP_GLOBAL_DEFAULTS[cmd_id]
        # Act
        sequence = spec.get("sequence")
        # Assert
        assert isinstance(sequence, str) and sequence != "", f"{cmd_id} missing sequence"

    @pytest.mark.parametrize("cmd_id", sorted(KEYMAP_GLOBAL_DEFAULTS))
    def test_command_ids_are_namespaced_with_a_colon(self, cmd_id: str) -> None:
        # Arrange
        # Act
        has_namespace = ":" in cmd_id
        # Assert
        assert has_namespace, f"command id {cmd_id} should be namespaced (prefix:id)"

    @pytest.mark.parametrize(
        "expected_chord",
        [
            "Alt+A",
            "Alt+T",
            "Alt+Shift+T",
            "Alt+Right",
            "Alt+Left",
            "Alt+Shift+Right",
            "Alt+Shift+Left",
            "Ctrl+U",
        ],
    )
    def test_the_existing_keyboard_shortcut_chords_are_all_present(self, expected_chord: str) -> None:
        """Migration completeness: every chord in _KeyboardShortcuts.ts
        must have a corresponding default command, so an app switching from
        the old module to the keymap primitive loses no binding."""
        # Arrange
        sequences = {spec["sequence"] for spec in KEYMAP_GLOBAL_DEFAULTS.values()}
        # Act
        present = expected_chord in sequences
        # Assert
        assert present, (
            f"chord {expected_chord} from keyboard-shortcuts has no keymap default; "
            f"an app migrating to the keymap would silently lose it"
        )


class TestRenderKeymapInit:
    """The rendered <script> tag is a self-contained JSON payload."""

    def test_renders_a_json_script_tag(self) -> None:
        # Arrange
        app_id = "figrecipe"
        # Act
        out = render_keymap_init(app_id)
        # Assert
        assert '<script type="application/json"' in out

    def test_script_tag_id_carries_the_app_id(self) -> None:
        # Arrange
        app_id = "figrecipe"
        # Act
        out = render_keymap_init(app_id)
        # Assert
        assert f'id="stx-keymap-init-{app_id}"' in out

    def test_script_tag_is_closed(self) -> None:
        # Arrange
        out = render_keymap_init("figrecipe")
        # Act
        has_closing_tag = "</script>" in out
        # Assert
        assert has_closing_tag, "rendered tag has no closing </script>"

    @pytest.mark.parametrize("cmd_id", sorted(KEYMAP_GLOBAL_DEFAULTS))
    def test_payload_carries_every_global_default(self, cmd_id: str) -> None:
        # Arrange
        out = render_keymap_init("figrecipe")
        # Act
        payload = _payload(out)
        # Assert
        assert cmd_id in payload["defaults"], f"{cmd_id} missing from rendered payload"

    def test_payload_carries_the_app_id(self) -> None:
        # Arrange
        out = render_keymap_init("figrecipe")
        # Act
        payload = _payload(out)
        # Assert
        assert payload["app"] == "figrecipe"

    def test_payload_mode_is_none_by_default(self) -> None:
        # Arrange
        out = render_keymap_init("figrecipe")
        # Act
        payload = _payload(out)
        # Assert
        assert payload["mode"] is None

    def test_app_defaults_merge_over_globals(self) -> None:
        # Arrange
        app_defaults = {
            "figrecipe:save": {
                "label": "Save figure",
                "group": "Figure",
                "sequence": "Ctrl+S",
            },
        }
        out = render_keymap_init("figrecipe", app_defaults=app_defaults)
        # Act
        payload = _payload(out)
        # Assert
        assert "figrecipe:save" in payload["defaults"]

    def test_global_defaults_survive_app_default_merge(self) -> None:
        # Arrange
        app_defaults = {
            "figrecipe:save": {"label": "Save figure", "group": "Figure", "sequence": "Ctrl+S"},
        }
        out = render_keymap_init("figrecipe", app_defaults=app_defaults)
        # Act
        payload = _payload(out)
        # Assert
        assert "ai-panel:toggle" in payload["defaults"]

    def test_mode_is_carried_when_set(self) -> None:
        # Arrange
        out = render_keymap_init("figrecipe", mode="editor")
        # Act
        payload = _payload(out)
        # Assert
        assert payload["mode"] == "editor"

    def test_output_is_deterministic_for_same_inputs(self) -> None:
        # Arrange
        a = render_keymap_init("figrecipe")
        # Act
        b = render_keymap_init("figrecipe")
        # Assert
        assert a == b


class TestKeymapDefaultsReturnsCopy:
    """keymap_defaults() must not leak the module-level dict by reference."""

    def test_mutation_does_not_affect_the_module(self) -> None:
        # Arrange
        original_count = len(KEYMAP_GLOBAL_DEFAULTS)
        defaults = keymap_defaults()
        # Act
        defaults.pop(next(iter(defaults)))
        mutated_count = len(KEYMAP_GLOBAL_DEFAULTS)
        # Assert
        assert mutated_count == original_count, (
            "keymap_defaults() returned a live reference to the module dict; "
            "an app that popped a default mutated scitex_sdk.ui.keymap globally"
        )
