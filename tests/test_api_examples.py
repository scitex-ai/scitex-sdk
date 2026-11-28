"""API-K004: public_eligible examples run within their limits profile."""

from django.test import override_settings

from scitex_sdk.testing.api_examples import run_examples
from tests import _api_ops_tier as leaf

TARGET = "tests._api_ops_tier:PLUGIN"
EXAMPLES = {
    "calc.sums.run": {"limits": "stats-inline", "params": {"values": [1, 2]}},
    "calc.renders.create": {"limits": "light", "params": {"values": [1]}},
}


def test_examples_within_their_profile_pass():
    # Arrange
    examples = EXAMPLES
    # Act
    found = run_examples(leaf.PLUGIN, examples, target=TARGET)
    # Assert
    assert found == []


def test_a_public_eligible_operation_without_an_example_fails():
    # Arrange
    examples = {"calc.sums.run": EXAMPLES["calc.sums.run"]}
    # Act
    found = run_examples(leaf.PLUGIN, examples, target=TARGET)
    # Assert
    assert [v.operation_id for v in found] == ["calc.renders.create"]


def test_an_example_over_its_profile_fails():
    # Arrange
    tiny = {"stats-inline": {"wall_seconds": 0.0, "cpu_seconds": 0.0}}
    # Act
    with override_settings(SCITEX_API_LIMITS_PROFILES=tiny):
        found = run_examples(leaf.PLUGIN, EXAMPLES, target=TARGET)
    # Assert
    assert [v.rule for v in found] == ["API-K004"]


def test_an_example_for_a_member_operation_fails():
    # Arrange
    examples = {**EXAMPLES, "calc.notes.create": {"params": {"values": [1]}}}
    # Act
    found = run_examples(leaf.PLUGIN, examples, target=TARGET)
    # Assert
    assert "non-public_eligible" in found[0].message
