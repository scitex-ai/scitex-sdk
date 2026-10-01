#!/usr/bin/env python3
"""ThemeProvider component metadata."""

from .._registry import register_component


class ThemeProvider:
    """Light/dark theme manager with semantic color tokens.

    Manages the data-theme attribute on <html>, persists preference
    to localStorage, and provides toggle/set/get API.

    TypeScript entry: scitex_sdk/ui/ts/shell/theme-provider/index.ts
    CSS: scitex_sdk/ui/css/shell/theme.css
    """

    name = "theme-provider"
    version = "0.1.0"
    description = "Light/dark theme manager with semantic color tokens"
    ts_entry = "scitex_sdk/ui/ts/shell/theme-provider/index"
    css_file = "scitex_sdk/ui/css/shell/theme.css"


register_component(ThemeProvider.name, ThemeProvider)
