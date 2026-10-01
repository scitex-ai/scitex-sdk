#!/usr/bin/env python3
"""Tests for ScitexUiConfig element-inspector auto-wiring.

Regression guard for the copy-paste settings drift that left some GUI apps
without Alt+I: a consumer that lists ``scitex_ui`` in ``INSTALLED_APPS`` but
does NOT hand-wire the middleware/context processor must still end up with
both after ``ready()`` runs. The wiring helpers are pure settings-mutation,
so they are tested directly against a lightweight fake settings object (no
Django boot / global ``settings.configure`` needed).
"""

import types

from scitex_sdk.ui.apps import (
    _CONTEXT_PROCESSOR,
    _MIDDLEWARE,
    _ensure_context_processor,
    _ensure_middleware,
)


def _settings(middleware, context_processors):
    return types.SimpleNamespace(
        MIDDLEWARE=list(middleware),
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {"context_processors": list(context_processors)},
            }
        ],
    )


# --- middleware auto-wire ----------------------------------------------

def test_middleware_appended_when_absent():
    # Arrange
    s = _settings(["django.middleware.common.CommonMiddleware"], [])
    # Act
    _ensure_middleware(s)
    # Assert
    assert _MIDDLEWARE in s.MIDDLEWARE


def test_middleware_not_duplicated():
    # Arrange
    s = _settings([_MIDDLEWARE], [])
    # Act
    _ensure_middleware(s)
    # Assert
    assert s.MIDDLEWARE.count(_MIDDLEWARE) == 1


def test_middleware_tuple_is_handled():
    # Arrange
    s = types.SimpleNamespace(MIDDLEWARE=("a.B",))
    # Act
    _ensure_middleware(s)
    # Assert
    assert list(s.MIDDLEWARE) == ["a.B", _MIDDLEWARE]


def test_middleware_missing_setting_is_noop():
    # Arrange
    s = types.SimpleNamespace()
    # Act
    _ensure_middleware(s)
    # Assert
    assert not hasattr(s, "MIDDLEWARE")


# --- context-processor auto-wire ---------------------------------------

def test_context_processor_appended_when_absent():
    # Arrange
    s = _settings([], ["django.template.context_processors.request"])
    # Act
    _ensure_context_processor(s)
    # Assert
    assert _CONTEXT_PROCESSOR in s.TEMPLATES[0]["OPTIONS"]["context_processors"]


def test_context_processor_not_duplicated():
    # Arrange
    s = _settings([], [_CONTEXT_PROCESSOR])
    # Act
    _ensure_context_processor(s)
    # Assert
    assert (
        s.TEMPLATES[0]["OPTIONS"]["context_processors"].count(_CONTEXT_PROCESSOR)
        == 1
    )


def test_context_processor_skips_non_django_backend():
    # Arrange
    s = types.SimpleNamespace(
        TEMPLATES=[
            {"BACKEND": "django.template.backends.jinja2.Jinja2", "OPTIONS": {}}
        ]
    )
    # Act
    _ensure_context_processor(s)
    # Assert
    assert "context_processors" not in s.TEMPLATES[0]["OPTIONS"]


def test_context_processor_missing_templates_is_noop():
    # Arrange
    s = types.SimpleNamespace()
    # Act
    _ensure_context_processor(s)
    # Assert
    assert not hasattr(s, "TEMPLATES")
