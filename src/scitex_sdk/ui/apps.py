#!/usr/bin/env python3
"""Django registration for the SDK-owned UI component.

Install scitex_sdk.ui in INSTALLED_APPS. Its app label is the namespaced
scitex_sdk_ui, so it installs alongside the retired scitex-ui package
without a duplicate-label conflict (ui ships no models, so the rename is
migration-free). ScitexUiConfig.ready() wires the development element
inspector and
feature context processors; middleware gates their visibility at runtime.
SCITEX_UI_AUTOWIRE_INSPECTOR=False explicitly disables automatic registration.
"""

from django.apps import AppConfig

_MIDDLEWARE = "scitex_sdk.ui.middleware.ElementInspectorMiddleware"
_CONTEXT_PROCESSOR = "scitex_sdk.ui.context_processors.element_inspector"
#: The generic development-feature visibility processor (L628): exposes
#: ``stx_dev_features`` so any dev-only surface can be gated without
#: re-deriving the DEBUG/staff/override precedence per feature.
_DEV_FEATURES_PROCESSOR = "scitex_sdk.ui.context_processors.dev_features"


def _ensure_middleware(settings) -> None:
    """Append :class:`ElementInspectorMiddleware` to ``settings.MIDDLEWARE``.

    No-op when ``MIDDLEWARE`` is unset or already contains the entry. The
    middleware is self-gating and injects into ``text/html`` responses, so
    it equips even apps that do not extend the shared shell.
    """
    middleware = getattr(settings, "MIDDLEWARE", None)
    if middleware is None or _MIDDLEWARE in middleware:
        return
    settings.MIDDLEWARE = [*middleware, _MIDDLEWARE]


def _ensure_context_processor(settings) -> None:
    """Append the element-inspector and dev-features context processors to
    Django template engines that lack them (keeps the ``{% include %}`` partial
    path and the generic ``stx_dev_features`` gate working).

    Skips non-Django backends (e.g. Jinja2) and engines without a
    ``context_processors`` list. The middleware de-dupes, so this is belt
    and suspenders rather than a second injection.
    """
    templates = getattr(settings, "TEMPLATES", None)
    if not templates:
        return
    for engine in templates:
        if "DjangoTemplates" not in engine.get("BACKEND", ""):
            continue
        options = engine.setdefault("OPTIONS", {})
        processors = options.get("context_processors")
        if processors is None:
            # No processor list at all: create it carrying both of ours.
            options["context_processors"] = [
                _CONTEXT_PROCESSOR,
                _DEV_FEATURES_PROCESSOR,
            ]
            continue
        # Already lists our element-inspector processor: the generic
        # dev-features one was introduced later, so add it if missing rather
        # than assuming the two are always wired together.
        existing = list(processors)
        if _CONTEXT_PROCESSOR not in existing:
            existing.append(_CONTEXT_PROCESSOR)
        if _DEV_FEATURES_PROCESSOR not in existing:
            existing.append(_DEV_FEATURES_PROCESSOR)
        options["context_processors"] = existing


class ScitexUiConfig(AppConfig):
    name = "scitex_sdk.ui"
    label = "scitex_sdk_ui"
    verbose_name = "SciTeX UI Components"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Auto-wire the element inspector unless explicitly opted out.

        Runs once during ``django.setup()`` — before the middleware stack is
        loaded (``BaseHandler.load_middleware``) and before template engines
        are instantiated — so the appended entries take effect. The
        middleware is self-gating via
        :func:`scitex_sdk.ui.context_processors.element_inspector_enabled` (a
        no-op in production) and de-dupes against templates that already
        include the partial. Opt out with
        ``SCITEX_UI_AUTOWIRE_INSPECTOR = False``.
        """
        from django.conf import settings

        if not getattr(settings, "SCITEX_UI_AUTOWIRE_INSPECTOR", True):
            return
        _ensure_middleware(settings)
        _ensure_context_processor(settings)
