#!/usr/bin/env python3
"""AlertBanner component metadata."""

from .._registry import register_component


class AlertBanner:
    """Dismissible alert / error banner, fixed to the top of the viewport.

    Variants for error and info; carries icon, body and close slots.
    Layered above ConfirmModal so an error raised by a modal action
    stays visible.

    CSS-only: no TypeScript entry. Apps drive it with their own handler.
    CSS: scitex_sdk/ui/css/app/alert-banner.css
    """

    name = "alert-banner"
    version = "0.1.0"
    description = "Dismissible top-fixed alert / error banner"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/alert-banner.css"


register_component(AlertBanner.name, AlertBanner)
