"""Tests for the UI-101..107 Rule corpus."""

from __future__ import annotations

import pytest

from scitex_sdk.ui._linter._rules import CATEGORY, build_rules

# Derived, NOT hand-listed: a new rule is auto-enrolled in every invariant
# below, so adding one can never silently exempt it from the bar its siblings
# meet. The roster assertion in `test_build_rules_returns_the_declared_corpus`
# stays hand-written on purpose — that one is the deliberate "you added a rule,
# acknowledge it" gate, and deriving it too would make it vacuous.
ALL_RULE_IDS = sorted(build_rules())


def test_build_rules_returns_the_declared_corpus():
    # Arrange — this gate did its job when UI-107 was added: it failed, and so
    # did the severity table and the plugin roster, which is the acknowledgement
    # it exists to force. Renamed off "six" because a name carrying the count
    # goes stale at the first addition while the assertion below does not.
    rules = build_rules()
    # Act
    ids = set(rules.keys())
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


def test_all_rules_share_ui_category():
    # Arrange
    rules = build_rules()
    # Act
    cats = {r.category for r in rules.values()}
    # Assert
    assert cats == {CATEGORY} == {"ui"}


# Hand-written on purpose: severity is a per-rule policy decision, not an
# invariant, so it cannot be derived. `test_severity_table_covers_every_rule`
# below keeps the table honest — a new rule with no entry here fails loudly
# instead of quietly going unchecked.
_EXPECTED_SEVERITIES = [
    ("STX-UI101", "warning"),
    ("STX-UI102", "warning"),
    ("STX-UI103", "warning"),
    # UI-104 is intentionally WARN in the current scitex-ui release.
    # The severity flip to ERROR is scheduled for scitex-ui 0.7.0;
    # this test guards the current release surface — when 0.7.0 lands,
    # this parameter flips to "error" with the version bump.
    ("STX-UI104", "warning"),
    ("STX-UI105", "warning"),
    ("STX-UI106", "warning"),
    # UI-107 is the corpus's FIRST error, and that is a measurement, not a
    # mood: the population when it shipped was 12 root-anchored API literals
    # across 3 consumer repos — small enough for those repos to clear. A rule
    # whose first run is red gets disabled rather than obeyed, so "error"
    # would have been the wrong call at, say, the 50 literals scitex-cloud
    # carries (which are not violations anyway — the hub IS the mount root).
    ("STX-UI107", "error"),
]


def test_severity_table_covers_every_rule():
    # Arrange — without this, adding a rule and forgetting a severity entry
    # leaves it untested while the suite stays green.
    # Act
    tabled = {rule_id for rule_id, _ in _EXPECTED_SEVERITIES}
    # Assert
    assert tabled == set(ALL_RULE_IDS)


@pytest.mark.parametrize("rule_id,expected_severity", _EXPECTED_SEVERITIES)
def test_rule_severity_matches_current_release(rule_id, expected_severity):
    # Arrange
    rules = build_rules()
    # Act
    rule = rules[rule_id]
    # Assert
    assert rule.severity == expected_severity


def test_ui104_message_documents_severity_flip_keyword():
    # Arrange — UI-104 must self-document the WARN → ERROR migration plan
    # so users see it in `scitex-linter list-rules` output, not only in
    # the SKILL doc. This guards against silent severity flips.
    rules = build_rules()
    # Act
    msg_lower = rules["STX-UI104"].message.lower()
    # Assert
    assert "warning → error" in msg_lower or "warning to error" in msg_lower


def test_ui104_message_documents_severity_flip_version_number():
    # Arrange — the flip date (scitex-ui 0.7.0) must appear inline; the
    # version number is the most operator-actionable bit of the warning.
    rules = build_rules()
    # Act
    msg = rules["STX-UI104"].message
    # Assert
    assert "0.7" in msg


@pytest.mark.parametrize(
    "rule_id", ALL_RULE_IDS
)
def test_all_rules_carry_requires_scitex_sdk_marker(rule_id):
    # Arrange — mirrors scitex-io's plugin convention so the linter knows
    # the rules require the SDK distribution that owns these UI components.
    rules = build_rules()
    # Act
    rule = rules[rule_id]
    # Assert
    assert rule.requires == "scitex-sdk"


@pytest.mark.parametrize(
    "rule_id", ALL_RULE_IDS
)
def test_each_rule_suggestion_is_non_trivial_length(rule_id):
    # Arrange — every rule must teach the fix, not just the violation.
    rules = build_rules()
    # Act
    suggestion = rules[rule_id].suggestion or ""
    # Assert
    assert len(suggestion) > 40


@pytest.mark.parametrize(
    "rule_id", ALL_RULE_IDS
)
def test_each_rule_suggestion_mentions_component_or_token(rule_id):
    # Arrange — the suggestion must point at a concrete fix surface.
    rules = build_rules()
    # Act
    lowered = (rules[rule_id].suggestion or "").lower()
    # Assert
    assert (
        "var(--" in lowered
        or "scitex_sdk.ui." in lowered
        or "scitex-sdk ui" in lowered
        or "dropdown" in lowered
    )


def test_ui106_suggestion_names_the_feature_detected_global():
    # Arrange — consumers feature-detect `window.STX.Combobox` before layering
    # the enhancement, so a suggestion that only says "use the combobox" leaves
    # the reader unable to write the guard.
    rules = build_rules()
    # Act
    suggestion = rules["STX-UI106"].suggestion or ""
    # Assert
    assert "window.STX.Combobox" in suggestion
