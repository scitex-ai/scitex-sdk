#!/usr/bin/env python3
"""Drawer component metadata."""

from .._registry import register_component


class Drawer:
    """Off-canvas panel with a scrim, keyboard-complete.

    Harvested from scitex-cards' chat.js mobile drawer at their request — the
    operator reads chat on a phone, where the agent list is this drawer.

    THE DEFECT THAT MATTERS: the source hid the closed panel with
    ``transform: translateX(-105%)`` and nothing else. A transform moves
    pixels; it does not remove an element from the tab order or the
    accessibility tree. Tabbing from the header walked focus into an invisible
    agent list — no visible ring, and the next Enter activated an unseen link.
    Closed means ``inert`` here, with ``visibility: hidden`` so the panel is
    also out of hit-testing. Neither implies the other, so both are set.

    Also fixed rather than carried across:

    - No Escape handler. An overlay openable by keyboard but closable only by
      pointer is a trap.
    - Focus was never moved in on open nor restored on close.
    - Tab was not trapped, so focus left the open drawer for the page behind
      the scrim.
    - ``.open`` was toggled independently on the panel and the scrim, so any
      path clearing one without the other desynchronised them — after which a
      single click put them in OPPOSITE states. One boolean owns the state and
      both elements are rendered from it.
    - The trigger carried no ``aria-expanded``.

    The scrim is created and owned by the component; the source required a
    hand-placed ``<div id="scrim">`` in every template.

    The source also scoped the whole drawer inside ``@media (max-width: 720px)``.
    That breakpoint is the consuming layout's decision, not the component's, so
    it lives in the app stylesheet.

    TS:  scitex_sdk/ui/ts/app/drawer/index
    CSS: scitex_sdk/ui/css/app/drawer.css
    """

    name = "drawer"
    version = "0.1.0"
    description = "Off-canvas drawer with scrim, inert-when-closed and focus trap"
    ts_entry = "scitex_sdk/ui/ts/app/drawer/index"
    css_file = "scitex_sdk/ui/css/app/drawer.css"


register_component(Drawer.name, Drawer)
