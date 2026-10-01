#!/usr/bin/env python3
"""AppShell component metadata."""

from .._registry import register_component


class AppShell:
    """Workspace layout shell with collapsible sidebar.

    Creates the three-zone layout: sidebar, main content area,
    and status bar slot. Supports app-specific accent colors.

    TypeScript entry: scitex_sdk/ui/ts/shell/app-shell/index.ts
    CSS: scitex_sdk/ui/css/shell/app-shell.css
    """

    name = "app-shell"
    version = "0.1.0"
    description = "Workspace layout shell with collapsible sidebar"
    ts_entry = "scitex_sdk/ui/ts/shell/app-shell/index"
    css_file = "scitex_sdk/ui/css/shell/app-shell.css"


register_component(AppShell.name, AppShell)
