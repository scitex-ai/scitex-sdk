#!/usr/bin/env python3
"""``{% scitex_js_catalog "<app package>" %}`` embeds that app's djangojs catalog."""

from __future__ import annotations

import sys

from django import template
from django.utils.html import json_script

from scitex_sdk.ui.i18n import js_catalog, js_catalog_element_id

register = template.Library()
_DOCUMENT_CATALOGS = object()


@register.simple_tag
def scitex_js_catalog(*packages: str):
    """Render the active language's JS catalog as a json_script element."""
    return json_script(js_catalog(packages), js_catalog_element_id(packages))


_compile_catalog = register.tags["scitex_js_catalog"]


def _inside_document_filter(document_frame):
    # A standard FilterNode buffers its child output before applying a filter.
    # Its template may include this tag indirectly, so parser-local detection
    # cannot establish that the JSON script will reach the document unchanged.
    filter_node = getattr(getattr(template, "defaulttags", None), "FilterNode", None)
    render_code = getattr(getattr(filter_node, "render", None), "__code__", None)
    get_frame = getattr(sys, "_getframe", None)
    if render_code is None or get_frame is None:
        return True

    # Inspect only the known Django render method's context local. Match the
    # outer RenderContext frame so a separate nested document does not inherit
    # this document's buffering status. No frame references outlive this call.
    frame = get_frame(1)
    try:
        while frame is not None:
            if frame.f_code is render_code:
                owner = frame.f_locals.get("context")
                frames = getattr(getattr(owner, "render_context", None), "dicts", ())
                if len(frames) > 1 and frames[1] is document_frame:
                    return True
            frame = frame.f_back
        return False
    finally:
        del frame


def _document_catalog_state(context):
    frames = context.render_context.dicts
    if len(frames) < 2:
        return None
    # Django pushes a frame for the outer Template.render(), then additional
    # frames for includes (also copied by include-only). The outer frame is
    # shared by this document and popped afterward, even for a reused Context.
    state = frames[1].setdefault(
        _DOCUMENT_CATALOGS,
        {
            "emitted": set(), "catalog": {}, "language": None, "plural": None,
            "captured": False,
        },
    )
    if not state["captured"] and _inside_document_filter(frames[1]):
        # Even a nontransforming standard filter is conservatively buffered.
        # Preserve later output; arbitrary custom buffering is not inferred.
        state["captured"] = True
    return state


class _CatalogNode(template.Node):
    def __init__(self, node):
        self.node = node

    def render(self, context):
        state = _document_catalog_state(context)
        # A simple_tag capture stores markup without emitting it. Preserve that
        # contract rather than suppressing a later, actually emitted catalog.
        if self.node.target_var is not None:
            if state is not None:
                # The variable may be interpolated anywhere later in the page.
                # Its placement cannot be observed by this tag, so retain later
                # output instead of changing the existing loader's precedence.
                state["captured"] = True
            return self.node.render(context)

        packages, _ = self.node.get_resolved_arguments(context)
        payload = js_catalog(packages)
        markup = json_script(payload, js_catalog_element_id(packages))
        if state is None or state["captured"]:
            return markup
        entries = payload["catalog"]
        plural = payload["plural"]
        if (
            markup in state["emitted"]
            and payload["language"] == state["language"]
            and (plural is None or plural == state["plural"])
            and all(state["catalog"].get(key) == value for key, value in entries.items())
        ):
            return ""

        # The existing gettext loader merges catalogs in document order, with
        # later values winning. Re-emit if an intervening catalog changed values
        # or language/plural information; only redundant identical output is lost.
        state["emitted"].add(markup)
        state["catalog"].update(entries)
        state["language"] = payload["language"]
        if plural is not None:
            state["plural"] = plural
        return markup


@register.tag("scitex_js_catalog")
def _catalog_tag(parser, token):
    return _CatalogNode(_compile_catalog(parser, token))


# EOF
