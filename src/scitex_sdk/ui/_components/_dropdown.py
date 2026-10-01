#!/usr/bin/env python3
"""Dropdown component metadata."""

from .._registry import register_component


class Dropdown:
    name = "dropdown"
    version = "0.1.0"
    description = "Context menu dropdown attached to a trigger element"
    ts_entry = "scitex_sdk/ui/ts/app/dropdown/index"
    css_file = "scitex_sdk/ui/css/app/dropdown.css"


register_component(Dropdown.name, Dropdown)
