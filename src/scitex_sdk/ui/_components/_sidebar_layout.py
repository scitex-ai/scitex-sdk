#!/usr/bin/env python3
"""SidebarLayout component metadata."""

from .._registry import register_component


class SidebarLayout:
    """Two-zone sidebar + content layout, with an optional nav list.

    `.stx-app-sidebar-layout` is the flex frame; the content zone has a
    `--centered` variant, and `.stx-app-sidebar-nav` styles the nav items
    and their badges.

    CSS-only: no TypeScript entry.
    CSS: scitex_sdk/ui/css/app/sidebar-layout.css
    """

    name = "sidebar-layout"
    version = "0.1.0"
    description = "Sidebar + content layout frame with nav list styling"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/sidebar-layout.css"


register_component(SidebarLayout.name, SidebarLayout)
