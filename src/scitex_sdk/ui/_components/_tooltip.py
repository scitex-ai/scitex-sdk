#!/usr/bin/env python3
"""Tooltip component metadata."""

from .._registry import register_component


class Tooltip:
    name = "tooltip"
    version = "0.1.0"
    description = "Auto-positioned tooltip system using data-tooltip attributes"
    ts_entry = "scitex_sdk/ui/ts/app/tooltip/index"
    css_file = "scitex_sdk/ui/css/app/tooltip.css"


register_component(Tooltip.name, Tooltip)
