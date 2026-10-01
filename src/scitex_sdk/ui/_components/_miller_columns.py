#!/usr/bin/env python3
"""MillerColumns component metadata."""

from .._registry import register_component


class MillerColumns:
    """Finder-style multi-column browser.

    A horizontal run of `.stx-app-miller__col` columns, optionally ending
    in a `--detail` column for the selected leaf.

    CSS-only: no TypeScript entry. Apps own selection and column spawning.
    CSS: scitex_sdk/ui/css/app/miller-columns.css
    """

    name = "miller-columns"
    version = "0.1.0"
    description = "Finder-style multi-column browser with detail column"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/miller-columns.css"


register_component(MillerColumns.name, MillerColumns)
