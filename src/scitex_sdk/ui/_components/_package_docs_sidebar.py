#!/usr/bin/env python3
"""PackageDocsSidebar component metadata."""

from .._registry import register_component


class PackageDocsSidebar:
    """Navigable sidebar showing SciTeX Python package documentation.

    Fetches package data from a JSON API and renders a grouped,
    clickable sidebar. Reusable by any SciTeX app.

    TypeScript entry: scitex_sdk/ui/ts/app/package-docs-sidebar/index.ts
    CSS: scitex_sdk/ui/css/app/package-docs-sidebar.css
    API: /apps/docs/api/packages/
    """

    name = "package-docs-sidebar"
    version = "0.1.0"
    description = "Navigable sidebar for Python package documentation"
    api_endpoint = "/apps/docs/api/packages/"
    ts_entry = "scitex_sdk/ui/ts/app/package-docs-sidebar/index"
    css_file = "scitex_sdk/ui/css/app/package-docs-sidebar.css"


register_component(PackageDocsSidebar.name, PackageDocsSidebar)
