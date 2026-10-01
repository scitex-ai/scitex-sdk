#!/usr/bin/env python3
"""Panes component metadata."""

from .._registry import register_component


class Panes:
    """One column per screen on phones, side by side on desktop.

    An app declares its columns as panes (``[data-stx-panes]`` with
    ``[data-stx-pane]`` children, or ``{% scitex_panes %}``/``{% scitex_pane %}``).
    At <=640px a sticky tab bar (icon + short label, 44px) switches the single
    visible pane; a horizontal swipe moves to the adjacent tab unless it starts
    in a horizontal scroller or a text field. The active pane is remembered per
    app in sessionStorage; ``window.stxPanes.show(id)`` switches it from code and
    ``stx-panes:change`` reports each switch. ``<details class="stx-acc">`` is the
    accordion for secondary settings inside a pane.

    CSS: scitex_sdk/ui/css/app/panes.css
    """

    name = "panes"
    version = "0.1.0"
    description = (
        "Multi-column app layout that becomes one pane per screen with a tab bar "
        "on phones; stxPanes.show(id), stx-panes:change, .stx-acc accordion"
    )
    ts_entry = "scitex_sdk/ui/ts/app/panes/index"
    css_file = "scitex_sdk/ui/css/app/panes.css"
    # Pre-built module for pages without a bundler; also sets window.stxPanes and auto-mounts.
    js_file = "scitex_sdk/ui/js/app/panes.js"


register_component(Panes.name, Panes)
