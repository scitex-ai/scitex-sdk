#!/usr/bin/env python3
"""scitex-sdk ui Django middleware.

``ElementInspectorMiddleware`` is the zero-friction way to make the
element inspector (Alt+I / Ctrl+I visual debugging overlay) available in a
Django app. Add a single line to ``MIDDLEWARE`` and the inspector's
``<link>`` + ``<script>`` are injected into every ``text/html`` response —
no per-app context-processor registration and no per-template
``{% include "scitex_sdk/ui/_element_inspector.html" %}`` needed::

    MIDDLEWARE = [
        ...
        "scitex_sdk.ui.middleware.ElementInspectorMiddleware",
    ]

To equip **every** scitex GUI app in develop + staging, add the line to
the shared settings and set the gate::

    SCITEX_UI_ELEMENT_INSPECTOR = SCITEX_ENV in {"development", "staging"}

Gating is delegated to :func:`scitex_sdk.ui.context_processors.element_inspector_enabled`,
so the middleware and the (still-supported) context-processor + partial
path stay in lock-step. The middleware never raises into a response: any
injection error is swallowed so a debug tool can never break a page.

This is a Django **hybrid (async-capable) middleware**: it adapts to the
mode of the inner chain. Under ASGI/daphne it runs natively async
(``async_capable = True``), so Django never has to bridge it with
``AsyncToSync`` in a thread-sensitive executor. That bridge is what caused
a hard deadlock — the event loop inside ``executor.shutdown()`` joining a
worker thread that was itself blocked in ``AsyncToSync`` waiting on the
loop — whenever daphne cancelled a slow request. Running native-async both
removes that deadlock and avoids the per-request sync↔async mode switch.
"""

from asgiref.sync import (
    iscoroutinefunction,
    markcoroutinefunction,
    sync_to_async,
)
from django.templatetags.static import static

from .context_processors import element_inspector_enabled


class ElementInspectorMiddleware:
    """Inject the element inspector into enabled HTML responses.

    Async-capable: mirrors the mode of ``get_response`` so no ``AsyncToSync``
    bridge is inserted under ASGI (see the module docstring for the deadlock
    this avoids).
    """

    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            # Tell Django's handler this instance is awaitable, so the inner
            # chain is handed to us as a coroutine (no sync adaptation).
            markcoroutinefunction(self)

    def __call__(self, request):
        if self.async_mode:
            # Return the coroutine; the ASGI handler awaits it on the loop.
            return self.__acall__(request)
        response = self.get_response(request)
        self._safe_inject(request, response)
        return response

    async def __acall__(self, request):
        response = await self.get_response(request)
        # The gate may read ``request.user`` — a lazy, DB-backed object under
        # ASGI whose evaluation is async-unsafe on the event loop and would
        # raise SynchronousOnlyOperation. Run the whole (sync) injection off
        # the loop so that access happens in a worker thread with no running
        # loop, where the sync DB read is permitted. This keeps
        # ``element_inspector_enabled`` the single source of truth for gating
        # instead of duplicating its precedence here.
        await sync_to_async(self._safe_inject)(request, response)
        return response

    def _safe_inject(self, request, response):
        try:
            self._maybe_inject(request, response)
        except Exception:
            # A debug/QA overlay must never break the actual response.
            pass

    def _maybe_inject(self, request, response):
        # Only rewrite non-streaming, un-encoded HTML documents.
        if getattr(response, "streaming", False):
            return
        if response.get("Content-Encoding"):
            return
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return
        if not element_inspector_enabled(request):
            return

        charset = response.charset or "utf-8"
        try:
            body = response.content.decode(charset, errors="ignore")
        except (AttributeError, UnicodeDecodeError):
            return

        # Respect an app that already wires the inspector via the partial.
        if "js/utils/element-inspector.js" in body:
            return

        idx = body.rfind("</body>")
        if idx == -1:
            return

        body = body[:idx] + self._snippet() + body[idx:]
        data = body.encode(charset)
        response.content = data
        if response.get("Content-Length") is not None:
            response["Content-Length"] = str(len(data))

    @staticmethod
    def _snippet() -> str:
        css = static("scitex_sdk/ui/css/utils/element-inspector.css")
        js = static("scitex_sdk/ui/js/utils/element-inspector.js")
        return (
            f'<link rel="stylesheet" href="{css}">'
            f'<script src="{js}" defer></script>\n'
        )
