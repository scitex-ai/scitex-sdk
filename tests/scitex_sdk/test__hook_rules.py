"""The SDK hook entry point produces real rules for the shared Dev contract."""

from importlib.metadata import entry_points

from scitex_dev.hooks import HookRule


def test_sdk_hook_provider_uses_the_shared_rule_contract():
    # Arrange: load only the SDK entry through its declared provider group.
    entry = next(
        ep for ep in entry_points(group="scitex_dev.hooks")
        if ep.name == "scitex-sdk"
    )
    # Act
    rules = entry.load()()
    # Assert: an absent/moved contract must not silently erase the SDK rules.
    assert rules and all(
        isinstance(rule, HookRule) and rule.provider == "scitex-sdk"
        for rule in rules
    )
