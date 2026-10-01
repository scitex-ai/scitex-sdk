#!/usr/bin/env python3
"""Badge component metadata."""

from .._registry import register_component


class Badge:
    """Standalone tonal pill for short status/type labels.

    Neutral by default; `--info` / `--success` / `--warning` / `--error`
    map onto the theme's `--status-*` variable triplets, and `--caps`
    gives an uppercase type-label variant.

    CSS-only: no TypeScript entry.
    CSS: scitex_sdk/ui/css/app/badge.css
    """

    name = "badge"
    version = "0.1.0"
    description = "Tonal pill badge with status tone and caps modifiers"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/badge.css"


register_component(Badge.name, Badge)
