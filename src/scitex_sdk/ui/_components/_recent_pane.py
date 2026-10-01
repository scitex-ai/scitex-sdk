#!/usr/bin/env python3
"""RecentPane component metadata."""

from .._registry import register_component


class RecentPane:
    """Real-time file-change feed pane.

    Entry rows with per-kind badges, filter buttons and an empty state.
    Originally scitex-cloud's repo-monitor component, generalised here.

    CSS-only: no TypeScript entry. Apps supply the event stream.
    CSS: scitex_sdk/ui/css/app/recent-pane.css
    """

    name = "recent-pane"
    version = "0.1.0"
    description = "Real-time file-change feed pane with filters and badges"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/recent-pane.css"


register_component(RecentPane.name, RecentPane)
