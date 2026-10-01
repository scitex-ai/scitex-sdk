#!/usr/bin/env python3
"""Template context processors for scitex-ui.

Install in Django settings to expose scitex-sdk ui flags to every template::

    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "scitex_sdk.ui.context_processors.element_inspector",
    ]

(When ``scitex_ui`` is in ``INSTALLED_APPS`` both the element-inspector
processor and the generic :func:`dev_features` processor are auto-wired by
``ScitexUiConfig.ready()`` — see ``apps.py`` — so hand-registration is a
fallback, not a requirement.)
"""

from django.conf import settings

#: This module's public surface. Declared rather than inferred, because
#: `from django.conf import settings` puts a LazySettings in module scope and
#: autodoc cannot introspect one before Django is configured — so without this
#: the docs build tries to document Django's settings object as ours and warns.
__all__ = [
    "element_inspector",
    "element_inspector_enabled",
    "dev_features",
    "feature_enabled",
    "DEV_FEATURE_NAMES",
]


#: The development-only features this package knows how to gate, by name.
#: This is the L628 "define the pattern" surface: a second dev-only feature
#: adds its name here (and, if it needs its own explicit knob, an entry to
#: ``_FEATURE_OVERRIDE_SETTINGS``). The gate itself, :func:`feature_enabled`,
#: is written once and shared by every feature — which is the point of the
#: compass item ("keep common UI rules in the SDK rather than fixing each app
#: independently", L18) applied to dev-gating.
DEV_FEATURE_NAMES = ("element-inspector",)


#: Per-feature explicit override setting, if any. A deployment sets this to
#: pin a feature on (develop/staging) or off (production) *independently of
#: ``DEBUG``. ``None`` means "no explicit knob for this feature" — the gate
#: then falls straight through to ``DEBUG`` / staff. The element-inspector
#: has historically exposed ``SCITEX_UI_ELEMENT_INSPECTOR``; that key is kept
#: for backward compatibility even though its name predates this registry.
_FEATURE_OVERRIDE_SETTINGS = {
    "element-inspector": "SCITEX_UI_ELEMENT_INSPECTOR",
}


def feature_enabled(request, name: str) -> bool:
    """Return whether a development-only feature should be active for a request.

    The standard dev-visibility gate (compass L628): development-only UI is
    hidden by default and shown on a deliberate, per-deployment signal.

    Precedence, first match wins:

    1. An explicit per-feature setting, when one is declared for ``name`` in
       ``_FEATURE_OVERRIDE_SETTINGS`` and is set (not ``None``). This is the
       knob deployments use to turn a feature on in develop + staging and off
       in production, independent of ``DEBUG``.
    2. ``settings.DEBUG`` — on for local development.
    3. Authenticated staff users — so a feature stays reachable in production
       for operators without exposing it to end users.
    4. Otherwise off.

    ``request.user`` may be a lazy, DB-backed object (unsafe to evaluate on an
    ASGI event loop), so this function is the single place that touches it.
    The element-inspector middleware runs the whole injection off the loop and
    delegates here, rather than re-reading the user itself — keeping one source
    of truth for the precedence.

    ``name`` is not validated against ``DEV_FEATURE_NAMES`` on purpose: this is
    the general mechanism, and a caller asking about a feature that isn't
    registered simply gets the ``DEBUG`` / staff answer (a feature with no
    explicit knob is dev-gated by default).
    """
    override_key = _FEATURE_OVERRIDE_SETTINGS.get(name)
    if override_key is not None:
        override = getattr(settings, override_key, None)
        if override is not None:
            return bool(override)
    if getattr(settings, "DEBUG", False):
        return True
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_staff", False)
    )


def element_inspector_enabled(request=None) -> bool:
    """Return whether the element inspector should load for this request.

    Single source of truth for the inspector's gating, shared by the
    :func:`element_inspector` context processor and
    :class:`scitex_sdk.ui.middleware.ElementInspectorMiddleware`.

    This is now a thin alias over the standard dev-visibility gate
    :func:`feature_enabled` (L628) with ``name="element-inspector"`` — its
    precedence (explicit ``SCITEX_UI_ELEMENT_INSPECTOR`` override →
    ``settings.DEBUG`` → staff → off) is exactly what ``feature_enabled``
    reproduces for that feature, so behavior is unchanged. Keeping it as a
    named function (rather than inlining the call) preserves the historical
    import surface and the middleware's single-source-of-truth contract.
    """
    return feature_enabled(request, "element-inspector")


def element_inspector(request):
    """Expose whether the Alt+I / Ctrl+I element inspector should load.

    Sets ``stx_element_inspector_enabled`` for ``_element_inspector.html``.
    Gating is delegated to :func:`element_inspector_enabled`. Safe default:
    if this processor is not installed the flag is simply absent (falsy) in
    templates, so nothing is loaded.
    """
    return {"stx_element_inspector_enabled": element_inspector_enabled(request)}


def dev_features(request):
    """Expose which development-only features are visible for this request.

    Sets ``stx_dev_features`` to the list of enabled feature names (e.g.
    ``["element-inspector"]`` in develop, ``[]`` in production). A template
    can gate any dev-only surface generically::

        {% if "some-feature" in stx_dev_features %} … {% endif %}

    rather than re-deriving the DEBUG/staff/override precedence per feature.
    Safe default: when no feature is enabled the list is empty, so any
    ``in stx_dev_features`` test is falsy and nothing dev-only renders.
    """
    return {
        "stx_dev_features": [
            name for name in DEV_FEATURE_NAMES if feature_enabled(request, name)
        ]
    }
