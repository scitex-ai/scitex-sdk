#!/usr/bin/env python3
"""SettingsCard component metadata."""

from .._registry import register_component


class SettingsCard:
    """Settings row rendered as a card, plus the grid that stacks them.

    Each card carries icon, name, description and a trailing arrow;
    `.stx-app-settings-grid` is the vertical container.

    CSS-only: no TypeScript entry.
    CSS: scitex_sdk/ui/css/app/settings-card.css
    """

    name = "settings-card"
    version = "0.1.0"
    description = "Settings row card with icon, description and grid container"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/settings-card.css"


register_component(SettingsCard.name, SettingsCard)
