#!/usr/bin/env python3
"""SelectorNav component metadata."""

from .._registry import register_component


class SelectorNav:
    """Vertical icon+label navigation strip.

    Items, labels and a pinned footer section; icon size follows
    `--ui-nav-icon-size`. Originally scitex-cloud's selector-nav.

    CSS-only: no TypeScript entry. Apps own the active item.
    CSS: scitex_sdk/ui/css/app/selector-nav.css
    """

    name = "selector-nav"
    version = "0.2.0"
    description = (
        "Hierarchical selector/navigation: one tree, rendered as a tab strip on "
        "desktop and a cascading dropdown on mobile (stxSelectorNav)"
    )
    ts_entry = "scitex_sdk/ui/ts/app/selector-nav/index"
    css_file = "scitex_sdk/ui/css/app/selector-nav.css"
    # Pre-built module for pages without a bundler; also auto-mounts every
    # [data-stx-selector-nav] root and sets window.stxSelectorNav.
    js_file = "scitex_sdk/ui/js/app/selector-nav.js"


register_component(SelectorNav.name, SelectorNav)
