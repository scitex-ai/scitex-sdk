#!/usr/bin/env python3
"""App Header component metadata."""

from .._registry import register_component


class AppHeader:
    """The ONE canonical app header row shared by every project-scoped app.

    Layout template: leaf title, leaf package version, the canonical
    project-selector slot, then app-specific actions. The version is read from
    the stable ``data-app-version`` mount metadata attribute (the scitex-app
    contract) rather than a leaf-local build constant, so a hub-mounted leaf
    still renders its own version.

    CSS: scitex_sdk/ui/css/app/app-header.css
    """

    name = "app-header"
    version = "0.1.0"
    description = (
        "Canonical app header: leaf title + leaf package version + the shared "
        "project-selector slot + app actions, one template for every app"
    )
    ts_entry = "scitex_sdk/ui/ts/app/app-header/index"
    css_file = "scitex_sdk/ui/css/app/app-header.css"
    # Pre-built module for pages without a bundler; also auto-mounts every
    # [data-stx-app-header] root and sets window.stxAppHeader.
    js_file = "scitex_sdk/ui/js/app/app-header.js"


register_component(AppHeader.name, AppHeader)
