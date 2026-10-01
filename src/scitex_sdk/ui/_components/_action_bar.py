#!/usr/bin/env python3
"""ActionBar component metadata."""

from .._registry import register_component


class ActionBar:
    """The phone bottom action bar, once.

    EXTRACTED FROM REAL IMPLEMENTATIONS, per the operator's 2026-09-14 YAGNI
    direction (card ui-mobile-layout-primitives-extract-from-apps-20260914).
    scitex-writer shipped this shape first in ``static/writer/css/
    editor-mobile.css`` (``.writer-mobile-actions``); figrecipe's 390px layout
    was the second input and needed no bar, which is why this is one primitive
    rather than the four the original plan text listed.

    It exists to stop three things being re-derived per app:

    * the bar sits above the hub's site dock and the iOS home indicator
      (``--site-dock-clearance`` + ``--stx-safe-inset-bottom``);
    * its height is RESERVED for the content, and the published
      ``--stx-action-bar-height`` is MEASURED from the rendered bar rather than
      a constant, because a translated label makes the real bar taller and a
      hardcoded 56px then hides the last line;
    * the reservation goes on the consumer's own container
      (``.stx-action-bar-space``), never on body/html/:root — the launcher
      overlay shares this edge and forbids a reserved band on the page.

    TS:  scitex_sdk/ui/ts/app/action-bar/index
    CSS: scitex_sdk/ui/css/app/action-bar.css
    JS:  scitex_sdk/ui/js/app/action-bar.js
    """

    name = "action-bar"
    version = "0.1.0"
    description = (
        "Bottom action bar for phone layouts: fixed above the site dock and the "
        "gesture bar, 44px items, and a measured --stx-action-bar-height the "
        "content reserves with .stx-action-bar-space"
    )
    ts_entry = "scitex_sdk/ui/ts/app/action-bar/index"
    css_file = "scitex_sdk/ui/css/app/action-bar.css"
    js_file = "scitex_sdk/ui/js/app/action-bar.js"


register_component(ActionBar.name, ActionBar)
