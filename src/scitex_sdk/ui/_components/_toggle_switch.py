#!/usr/bin/env python3
"""ToggleSwitch component metadata."""

from .._registry import register_component


class ToggleSwitch:
    """Checkbox-backed toggle switch, with a small (`--sm`) size variant.

    Wraps a native `<input type="checkbox">` so it stays keyboard- and
    form-native; the slider is styled from the input state.

    CSS-only: no TypeScript entry.
    CSS: scitex_sdk/ui/css/app/toggle-switch.css
    """

    name = "toggle-switch"
    version = "0.1.0"
    description = "Checkbox-backed toggle switch with small size variant"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/toggle-switch.css"


register_component(ToggleSwitch.name, ToggleSwitch)
