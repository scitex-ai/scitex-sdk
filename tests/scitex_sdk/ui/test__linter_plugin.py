"""Tests for the SDK UI linter plugin entry point.

Verifies the shape returned by ``get_plugin()`` matches the
``scitex_dev.linter._plugin_loader.load_plugins`` contract.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

import scitex_sdk.ui._linter_plugin as provider_module
from scitex_sdk.ui._linter_plugin import get_plugin


def test_get_plugin_returns_dict_with_expected_keys():
    # Arrange
    plugin = get_plugin()
    # Act
    keys = set(plugin.keys())
    # Assert
    assert keys == {"rules", "call_rules", "axes_hints", "checkers", "replaces"}


def test_get_plugin_ships_the_declared_corpus():
    # Arrange
    # the plugin roster is what scitex-dev's registry actually sees,
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
        "STX-UI108",
        "STX-UI109",
        "STX-UI110",
        "STX-UI111",
        "STX-UI112",
        "STX-UI113",
        "STX-UI114",
        "STX-UI115",
        "STX-UI116",
    }


def test_get_plugin_checkers_is_empty_list():
    # Arrange
    # scitex-dev's checker is Python-AST-only; UI rules
    # target CSS/HTML/TSX and are enforced via `scitex-ui lint`.
    plugin = get_plugin()
    # Act
    checkers = plugin["checkers"]
    # Assert
    assert checkers == []


def test_get_plugin_call_rules_is_empty_dict():
    # Arrange
    # UI rules are not call-pattern rules.
    plugin = get_plugin()
    # Act
    call_rules = plugin["call_rules"]
    # Assert
    assert call_rules == {}


def test_get_plugin_axes_hints_is_empty_dict():
    # Arrange
    # UI rules don't contribute axes hints.
    plugin = get_plugin()
    # Act
    axes_hints = plugin["axes_hints"]
    # Assert
    assert axes_hints == {}


def test_get_plugin_is_idempotent_rule_ids_are_stable():
    # Arrange
    # `load_plugins` may call get_plugin once and cache; the
    # function must be safe to call repeatedly with stable shape.
    first = get_plugin()
    second = get_plugin()
    # Act
    first_ids = sorted(r.id for r in first["rules"])
    second_ids = sorted(r.id for r in second["rules"])
    # Assert
    assert first_ids == second_ids


def test_get_plugin_is_idempotent_replaces_is_stable():
    # Arrange
    # `load_plugins` may call get_plugin once and cache; the
    # function must be safe to call repeatedly with stable shape.
    first = get_plugin()
    second = get_plugin()
    # Act
    # Assert
    assert first["replaces"] == second["replaces"]


def test_replacement_identifies_only_the_complete_predecessor_provider():
    """Seven SDK rules replace the exact old UI entry point as one corpus.

    The replaces contract is FROZEN at the predecessor's seven — new
    drift-pack rules (108+) are additive, not replacements, so extending
    the range here breaks the installed-registry check that pins the
    predecessor's complete advertised set.
    """
    # Arrange
    from scitex_dev.linter.spi import ProviderReplacement

    plugin = get_plugin()
    # Act
    replaces = plugin["replaces"]
    # Assert
    assert replaces == (
        ProviderReplacement(
            distribution="scitex-ui",
            entry_point="ui",
            value="scitex_ui._linter_plugin:get_plugin",
            rule_ids=tuple(f"STX-UI{number}" for number in range(101, 108)),
        ),
    )


def test_replacement_rule_ids_are_covered_by_the_plugin_corpus():
    # Arrange
    plugin = get_plugin()
    # Act
    replaced = set(plugin["replaces"][0].rule_ids)
    shipped = {rule.id for rule in plugin["rules"]}
    # Assert
    assert replaced <= shipped


def test_runtime_and_provider_imports_keep_dev_optional(tmp_path):
    """A real interpreter without site packages imports before activation."""
    # Arrange
    # Installed wheels may share a site-packages directory with Dev. Copy only
    # the SDK package so this interpreter sees the actual shipped SDK bytes
    # without inheriting any adjacent distribution.
    shutil.copytree(
        Path(provider_module.__file__).resolve().parents[1],
        tmp_path / "scitex_sdk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    source_root = str(tmp_path)
    code = f"""
import sys
sys.path.insert(0, {source_root!r})
import scitex_sdk
from scitex_sdk.ui._linter_plugin import get_plugin
assert not any(name == 'scitex_dev' or name.startswith('scitex_dev.') for name in sys.modules)
try:
    get_plugin()
except ImportError as error:
    assert 'scitex-dev>=0.62' in str(error), str(error)
    assert 'standalone' in str(error), str(error)
else:
    raise AssertionError('Provider activation requires its declared optional tooling SPI')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    # Act
    returncode = result.returncode
    # Assert
    assert returncode == 0, result.stderr


def _load_forward_and_reverse_rule_tables():
    """Shared arrange for the coexistence tests below.

    Exercises real installed entry points when the predecessor is present;
    skips when the SDK, legacy UI, and logging provider wheels are not all
    installed. Returns the (forward, reverse) loads.
    """
    from scitex_dev.linter._plugin_loader import load_plugins

    wanted = {
        ("scitex-logging", "scitex-logging", "scitex_logging._linter_plugin:get_plugin"),
        ("scitex-sdk", "ui", "scitex_sdk.ui._linter_plugin:get_plugin"),
        ("scitex-ui", "ui", "scitex_ui._linter_plugin:get_plugin"),
    }
    points = []
    found = set()
    for point in entry_points(group="scitex_dev.linter.plugins"):
        distribution = re.sub(r"[-_.]+", "-", point.dist.metadata["Name"]).lower()
        identity = (distribution, point.name, point.value)
        if identity in wanted:
            points.append(point)
            found.add(identity)
    if found != wanted:
        pytest.skip("Coexistence requires installed SDK, legacy UI, and logging provider wheels")

    forward = load_plugins(entry_points_iter=lambda: iter(points))
    reverse = load_plugins(entry_points_iter=lambda: iter(reversed(points)))
    return forward, reverse


def _ui_rules_of(forward):
    """Shared arrange: the UI-owned slice of a loaded rule table."""
    return {
        code: rule for code, rule in forward["rules"].items()
        if code.startswith("STX-UI")
    }


def test_installed_rule_tables_are_order_independent():
    """Exercise real installed entry points when the predecessor is present."""
    # Arrange
    forward, reverse = _load_forward_and_reverse_rule_tables()
    # Act
    # Assert
    assert forward["rules"] == reverse["rules"]


def test_installed_replacement_tables_are_order_independent():
    # Arrange
    forward, reverse = _load_forward_and_reverse_rule_tables()
    # Act
    # Assert
    assert forward["provider_replacements"] == reverse["provider_replacements"]


def test_installed_ui_rule_set_covers_ui101_to_ui116():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    ui_rules = _ui_rules_of(forward)
    # Assert — full UI101..UI116 corpus, no gaps.
    assert set(ui_rules) == {f"STX-UI{number}" for number in range(101, 117)}


def test_installed_ui_rules_require_the_sdk():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    ui_rules = _ui_rules_of(forward)
    # Assert
    assert all(rule.requires == "scitex-sdk" for rule in ui_rules.values())


def test_installed_coexistence_declares_exactly_one_replacement():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    replacements = forward["provider_replacements"]
    # Assert
    assert len(replacements) == 1


def test_installed_replacement_names_sdk_as_successor():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    receipt = forward["provider_replacements"][0]
    # Assert
    assert receipt["successor_distribution"] == "scitex-sdk"


def test_installed_replacement_names_ui_as_predecessor():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    receipt = forward["provider_replacements"][0]
    # Assert
    assert receipt["predecessor_distribution"] == "scitex-ui"


def test_installed_replacement_covers_only_the_predecessor_contract():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    receipt = forward["provider_replacements"][0]
    # Assert
    # The receipt covers the replaced predecessor contract only (101-107);
    # additive drift-pack rules (108+) are enforced, not replaced.
    assert set(receipt["rule_ids"]) == {f"STX-UI{number}" for number in range(101, 108)}


def test_installed_replacement_is_strictly_narrower_than_enforced_rules():
    # Arrange
    forward, _reverse = _load_forward_and_reverse_rule_tables()
    # Act
    receipt = forward["provider_replacements"][0]
    ui_rules = _ui_rules_of(forward)
    # Assert
    assert set(receipt["rule_ids"]) < set(ui_rules)
