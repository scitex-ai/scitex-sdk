#!/usr/bin/env python3
"""CollapsiblePanel component metadata."""

from .._registry import register_component


class CollapsiblePanel:
    """Collapsed-state styling for app split-panes.

    Apply `.stx-app-panel` to a pane container and toggle
    `.stx-app-panel--collapsed`; `.stx-app-panel__title` renders the
    vertical icon+label strip shown while collapsed.

    CSS-only: no TypeScript entry. Apps own the toggle.
    CSS: scitex_sdk/ui/css/app/collapsible-panel.css
    """

    name = "collapsible-panel"
    version = "0.1.0"
    description = "Collapsed-state styling for app split-panes"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/collapsible-panel.css"


register_component(CollapsiblePanel.name, CollapsiblePanel)
