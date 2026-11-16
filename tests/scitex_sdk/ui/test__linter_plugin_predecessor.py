"""The UI replacement contract follows the installed scitex-ui release.

scitex-dev refuses to run any linter when a declared replacement's rule IDs
differ from the predecessor's complete advertised set, so a stale scitex-ui
(e.g. 0.10.0, which advertises STX-UI101..105) next to the SDK used to break
every lint. The SDK may not pin ``scitex-ui>=0.14.0`` (requiring the retired
distribution fails the release ownership gate), so the declaration is keyed
on the installed release instead. The corpora below were read from the
published scitex-ui wheels on PyPI.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, entry_points, version

import pytest

from scitex_sdk.ui import _linter_plugin as provider

UI = "STX-UI{}".format


@pytest.mark.parametrize(
    "release,last_rule",
    [
        ("0.6.0", 105),
        ("0.10.0", 105),
        ("0.12.1", 105),
        ("0.13.0", 106),
        ("0.14.0", 107),
        ("0.15.0", 107),
        ("0.23.1", 107),
    ],
)
def test_declared_rule_ids_match_the_release_corpus(release, last_rule):
    # Arrange
    expected = tuple(UI(n) for n in range(101, last_rule + 1))
    # Act
    declared = provider.predecessor_rule_ids(release)
    # Assert
    assert declared == expected


def test_full_contract_floor_is_first_release_advertising_ui107():
    # Arrange
    full = tuple(UI(n) for n in range(101, 108))
    # Act
    floor = {provider.FULL_CONTRACT_FLOOR: provider.predecessor_rule_ids("0.14.0")}
    # Assert
    assert floor == {(0, 14, 0): full}


def test_absent_predecessor_declares_the_full_contract():
    # Arrange
    full = tuple(UI(n) for n in range(101, 108))
    # Act
    declared = provider.predecessor_rule_ids(None)
    # Assert
    assert declared == full


def test_every_declared_corpus_is_offered_by_the_sdk():
    # Arrange
    offered = {rule.id for rule in provider.get_plugin()["rules"]}
    # Act
    missing = {
        code
        for _floor, rule_ids in provider.PREDECESSOR_CORPORA
        for code in rule_ids
        if code not in offered
    }
    # Assert
    assert missing == set()


def _installed_predecessor_point():
    try:
        installed = version("scitex-ui")
    except PackageNotFoundError:
        pytest.skip("scitex-ui is not installed")
    for point in entry_points(group="scitex_dev.linter.plugins"):
        name = re.sub(r"[-_.]+", "-", point.dist.metadata["Name"]).lower()
        if name == "scitex-ui" and point.name == "ui":
            return installed, point
    pytest.skip("installed scitex-ui advertises no linter provider")


def test_declaration_equals_installed_predecessor_advertised_rules():
    # Arrange
    installed, point = _installed_predecessor_point()
    advertised = {rule.id for rule in point.load()()["rules"]}
    # Act
    declared = set(provider.get_plugin()["replaces"][0].rule_ids)
    # Assert
    assert declared == advertised, installed
