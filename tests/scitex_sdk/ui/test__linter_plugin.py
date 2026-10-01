"""Tests for the scitex-ui linter plugin entry point.

Verifies the shape returned by ``get_plugin()`` matches the
``scitex_dev.linter._plugin_loader.load_plugins`` contract.
"""

from __future__ import annotations

from scitex_sdk.ui._linter_plugin import get_plugin


def test_get_plugin_returns_dict_with_expected_keys():
    # Arrange
    plugin = get_plugin()
    # Act
    keys = set(plugin.keys())
    # Assert
    assert keys == {"rules", "call_rules", "axes_hints", "checkers"}


def test_get_plugin_ships_the_declared_corpus():
    # Arrange — the plugin roster is what scitex-dev's registry actually sees,
    # so this is the REACH assertion: a rule present in build_rules() but
    # missing here would be written, tested, and enforced nowhere. Verified
    # against the live registry too — 41 rules with UI-107, 40 without.
    plugin = get_plugin()
    # Act
    ids = {rule.id for rule in plugin["rules"]}
    # Assert
    assert ids == {
        "STX-UI101",
        "STX-UI102",
        "STX-UI103",
        "STX-UI104",
        "STX-UI105",
        "STX-UI106",
        "STX-UI107",
    }


def test_get_plugin_checkers_is_empty_list():
    # Arrange — scitex-dev's checker is Python-AST-only; UI rules
    # target CSS/HTML/TSX and are enforced via `scitex-ui lint`.
    plugin = get_plugin()
    # Act
    checkers = plugin["checkers"]
    # Assert
    assert checkers == []


def test_get_plugin_call_rules_is_empty_dict():
    # Arrange — UI rules are not call-pattern rules.
    plugin = get_plugin()
    # Act
    call_rules = plugin["call_rules"]
    # Assert
    assert call_rules == {}


def test_get_plugin_axes_hints_is_empty_dict():
    # Arrange — UI rules don't contribute axes hints.
    plugin = get_plugin()
    # Act
    axes_hints = plugin["axes_hints"]
    # Assert
    assert axes_hints == {}


def test_get_plugin_is_idempotent():
    # Arrange — `load_plugins` may call get_plugin once and cache; the
    # function must be safe to call repeatedly with stable shape.
    first = get_plugin()
    second = get_plugin()
    # Act
    first_ids = sorted(r.id for r in first["rules"])
    second_ids = sorted(r.id for r in second["rules"])
    # Assert
    assert first_ids == second_ids
