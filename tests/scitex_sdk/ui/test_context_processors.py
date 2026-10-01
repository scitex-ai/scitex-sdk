#!/usr/bin/env python3
"""Tests for the development-only feature visibility pattern (compass L628).

The pattern is the generic ``feature_enabled(request, name)`` gate plus the
``dev_features`` context processor, with the pre-existing element-inspector as
the first feature it is defined against. The behavioral contract is two-sided:

1. the NEW generic surface works (DEBUG / staff / explicit-override precedence,
   the per-feature override, the unregistered-name fallthrough, and the
   ``stx_dev_features`` list); and
2. the OLD element-inspector behavior is UNCHANGED — ``element_inspector_enabled``
   is now an alias over ``feature_enabled`` and must reproduce its historical
   precedence exactly. ``tests/scitex_sdk/ui/test_middleware.py`` already pins the
   inspector's middleware behavior; these pin the gate it delegates to.

Django is configured the same minimal way as ``test_middleware.py`` (no
pytest-django in this package's deps); the ``settings.configured`` guard keeps
the two files from colliding on import order.
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles"],
        DEFAULT_CHARSET="utf-8",
    )
    django.setup()

from django.test import override_settings  # noqa: E402

from scitex_sdk.ui.context_processors import (  # noqa: E402
    DEV_FEATURE_NAMES,
    _FEATURE_OVERRIDE_SETTINGS,
    dev_features,
    element_inspector_enabled,
    feature_enabled,
)


class _User:
    def __init__(self, authenticated, staff):
        self.is_authenticated = authenticated
        self.is_staff = staff


class _Req:
    def __init__(self, user=None):
        self.user = user


# --- the generic gate: precedence ------------------------------------------


def test_feature_off_by_default():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is False


def test_feature_on_in_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is True


def test_feature_on_for_staff_without_debug():
    # Arrange
    req = _Req(_User(authenticated=True, staff=True))
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is True


def test_feature_off_for_authenticated_non_staff():
    # Arrange
    req = _Req(_User(authenticated=True, staff=False))
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is False


def test_feature_off_for_anonymous():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is False


# --- the per-feature explicit override (takes precedence over DEBUG) --------


def test_feature_override_true_enables_without_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False, SCITEX_UI_ELEMENT_INSPECTOR=True):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is True


def test_feature_override_false_disables_even_in_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True, SCITEX_UI_ELEMENT_INSPECTOR=False):
        enabled = feature_enabled(req, "element-inspector")
    # Assert
    assert enabled is False


# --- the unregistered-name fallthrough (the L628 mechanism) -----------------


def test_unregistered_feature_on_in_debug():
    """A feature with no explicit override key gets the DEBUG / staff answer.

    This is the mechanism by which a SECOND dev-only feature opts into the
    standard gate without touching ``feature_enabled`` — the L628 point.
    """
    # Arrange
    other = "brand-new-dev-feature"  # not in _FEATURE_OVERRIDE_SETTINGS
    # Act
    with override_settings(DEBUG=True):
        enabled = feature_enabled(_Req(), other)
    # Assert
    assert enabled is True


def test_unregistered_feature_off_without_debug_or_staff():
    # Arrange
    other = "brand-new-dev-feature"
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(_Req(), other)
    # Assert
    assert enabled is False


def test_unregistered_feature_on_for_staff_without_debug():
    # Arrange
    other = "brand-new-dev-feature"
    # Act
    with override_settings(DEBUG=False):
        enabled = feature_enabled(_Req(_User(True, True)), other)
    # Assert
    assert enabled is True


def test_element_inspector_has_an_override_key():
    """The inspector keeps its historical explicit knob (backward compat)."""
    # Arrange
    # Act
    key = _FEATURE_OVERRIDE_SETTINGS.get("element-inspector")
    # Assert
    assert key == "SCITEX_UI_ELEMENT_INSPECTOR"


# --- behavior preservation: the alias is exact ------------------------------


def test_element_inspector_enabled_matches_the_gate_in_debug():
    # Arrange
    req = _Req(_User(authenticated=True, staff=False))
    # Act
    with override_settings(DEBUG=True):
        diverged = element_inspector_enabled(req) != feature_enabled(
            req, "element-inspector"
        )
    # Assert
    assert not diverged


def test_element_inspector_enabled_matches_the_gate_with_override_off():
    # Arrange
    req = _Req(_User(authenticated=True, staff=True))
    # Act
    with override_settings(DEBUG=True, SCITEX_UI_ELEMENT_INSPECTOR=False):
        diverged = element_inspector_enabled(req) != feature_enabled(
            req, "element-inspector"
        )
    # Assert
    assert not diverged


def test_element_inspector_enabled_matches_the_gate_with_override_on():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False, SCITEX_UI_ELEMENT_INSPECTOR=True):
        diverged = element_inspector_enabled(req) != feature_enabled(
            req, "element-inspector"
        )
    # Assert
    assert not diverged


def test_element_inspector_enabled_matches_the_gate_default_off():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False):
        diverged = element_inspector_enabled(req) != feature_enabled(
            req, "element-inspector"
        )
    # Assert
    assert not diverged


# --- the dev_features context processor -------------------------------------


def test_dev_features_lists_enabled_features_in_debug():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True):
        ctx = dev_features(req)
    # Assert
    assert ctx["stx_dev_features"] == list(DEV_FEATURE_NAMES)


def test_dev_features_empty_in_production():
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=False):
        ctx = dev_features(req)
    # Assert
    assert ctx["stx_dev_features"] == []


def test_dev_features_staff_sees_features_without_debug():
    # Arrange
    req = _Req(_User(authenticated=True, staff=True))
    # Act
    with override_settings(DEBUG=False):
        ctx = dev_features(req)
    # Assert
    assert ctx["stx_dev_features"] == list(DEV_FEATURE_NAMES)


def test_dev_features_respects_per_feature_override():
    """A feature pinned off by its explicit knob drops out of the list even
    in DEBUG, while others stay — the per-feature independence L628 wants."""
    # Arrange
    req = _Req()
    # Act
    with override_settings(DEBUG=True, SCITEX_UI_ELEMENT_INSPECTOR=False):
        ctx = dev_features(req)
    # Assert
    assert "element-inspector" not in ctx["stx_dev_features"]


def test_dev_feature_registry_is_not_vacuous():
    # Arrange
    # Act
    count = len(DEV_FEATURE_NAMES)
    # Assert
    assert count >= 1, (
        "DEV_FEATURE_NAMES is empty — the dev_features processor would always "
        "return [] and the pattern would be untestable"
    )
