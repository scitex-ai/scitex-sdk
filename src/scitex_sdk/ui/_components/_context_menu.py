#!/usr/bin/env python3
"""ContextMenu component metadata."""

from .._registry import register_component


class ContextMenu:
    """Right-click context menu: surface, items, dividers, danger variant — and behaviour.

    Supplies the surface, item states (including ``:disabled``), separator
    styling, a right-aligned ``__shortcut`` key hint and an uppercase
    ``__label`` section header.

    As of 0.3.0 the mechanics ship too, so apps no longer re-implement them:
    open-at-cursor with viewport clamping, dismissal on outside-click /
    Escape / scroll / resize / blur, and arrow-key navigation. Declare items
    as data; the module emits the markup this stylesheet expects.

    Consumable WITHOUT adopting the shell — link ``css/shell/theme.css`` for
    the design tokens plus this stylesheet.

    TS:  scitex_sdk/ui/ts/app/context-menu/index
    CSS: scitex_sdk/ui/css/app/context-menu.css
    """

    name = "context-menu"
    version = "0.3.0"
    description = (
        "Right-click context menu with items, dividers, shortcut hints, section "
        "labels, cursor positioning, dismissal and keyboard navigation"
    )
    ts_entry = "scitex_sdk/ui/ts/app/context-menu/index"
    css_file = "scitex_sdk/ui/css/app/context-menu.css"


register_component(ContextMenu.name, ContextMenu)
