#!/usr/bin/env python3
"""StatusBar component metadata."""

from .._registry import register_component


class StatusBar:
    """Bottom status bar with left/center/right sections.

    Displays status items with optional icons and click handlers.
    Designed for workspace-level information display.

    TypeScript entry: scitex_sdk/ui/ts/shell/status-bar/index.ts
    CSS: scitex_sdk/ui/css/shell/status-bar.css
    """

    name = "status-bar"
    version = "0.1.0"
    description = "Bottom status bar with left/center/right sections"
    ts_entry = "scitex_sdk/ui/ts/shell/status-bar/index"
    css_file = "scitex_sdk/ui/css/shell/status-bar.css"


register_component(StatusBar.name, StatusBar)
