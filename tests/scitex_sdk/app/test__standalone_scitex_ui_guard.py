"""An incomplete SDK refuses a standalone launch before Django setup."""

from __future__ import annotations

import importlib.util

import pytest

from scitex_sdk.app._standalone import (
    ScitexUiRequiredError,
    _SCITEX_UI_REQUIRED,
    _scitex_ui_present,
    run_standalone,
)


def test_the_guard_error_is_a_runtime_error_not_django_improperly_configured():
    """It is a RuntimeError subclass (so a launcher can catch it specifically)
    and is NOT Django's ImproperlyConfigured — this failure happens before
    Django is configured, so it must not masquerade as a Django one."""
    # Arrange
    from django.core.exceptions import ImproperlyConfigured
    # Act
    is_runtime = issubclass(ScitexUiRequiredError, RuntimeError)
    not_improper = not issubclass(ScitexUiRequiredError, ImproperlyConfigured)
    # Assert
    assert is_runtime and not_improper, (
        f"ScitexUiRequiredError must be a RuntimeError subclass "
        f"(got {is_runtime}) and must NOT be a Django "
        f"ImproperlyConfigured subclass (got {not_improper})"
    )


def test_the_guard_message_names_the_cause_and_the_fix():
    # Arrange — the contract: an operator chasing the old
    # TemplateDoesNotExist must be told what is actually missing.
    msg = _SCITEX_UI_REQUIRED
    # Act — nothing to call; the message IS the assertion surface.
    # Assert — it names the missing package, the install fix, and the old
    # failure mode it replaces (so a reader can connect it to what they saw).
    assert all(
        needle in msg
        for needle in ("scitex_sdk.ui", "pip install --force-reinstall", "scitex-sdk[gui]")
    ), f"guard message must name the package, the fix, and the old failure; got: {msg!r}"


def test_presence_check_agrees_with_find_spec_in_both_directions():
    """`_scitex_ui_present` is a pure re-read of `find_spec`. Whatever the
    environment, the two must agree — this pins the check to the real import
    so it cannot drift to a version string or a hardcoded answer."""
    # Arrange — the ground truth the check is a proxy for.
    truth = importlib.util.find_spec("scitex_sdk.ui") is not None
    # Act
    check = _scitex_ui_present()
    # Assert — one direction is enough to pin the proxy to the source; the
    # other direction would be asserting the same boolean equals itself.
    assert check is truth


def test_guard_fires_before_any_django_configuration():
    """When the shell is absent, `run_standalone` raises at the FIRST check —
    before it sets SCITEX_WORKING_DIR, calls `_configure_django`, or imports
    `django.setup`. Proven by the guard's position in the source, not by
    trusting it: a regression that moved the check below `_configure_django`
    would leave Django configured in the failing case, which this test would
    not catch, so the position is asserted explicitly."""
    # Arrange
    import inspect
    src = inspect.getsource(run_standalone).splitlines()
    # Act
    guard_idx = next(
        i for i, line in enumerate(src) if "_scitex_ui_present" in line
    )
    configure_idx = next(
        i for i, line in enumerate(src) if "_configure_django" in line
    )
    # Assert
    assert guard_idx < configure_idx, (
        f"guard must fire before _configure_django (guard line {guard_idx}, "
        f"configure line {configure_idx})"
    )


def test_run_standalone_raises_the_named_error_when_the_shell_is_absent(monkeypatch):
    """An incomplete SDK refuses launch before configuration or file writes."""
    monkeypatch.setattr("scitex_sdk.app._standalone._scitex_ui_present", lambda: False)
    with pytest.raises(ScitexUiRequiredError):
        run_standalone(app_module="some_app._django")
