#!/usr/bin/env python3
"""FileBrowser component metadata."""

from .._registry import register_component


class FileBrowser:
    """Tree view for navigating file hierarchies.

    Renders a collapsible file tree with directory expand/collapse,
    file selection, and file-type icons.

    TypeScript entry: scitex_sdk/ui/ts/app/file-browser/index.ts
    CSS: scitex_sdk/ui/css/app/file-browser.css
    """

    name = "file-browser"
    version = "0.1.0"
    description = "Tree view for navigating file hierarchies"
    ts_entry = "scitex_sdk/ui/ts/app/file-browser/index"
    css_file = "scitex_sdk/ui/css/app/file-browser.css"


register_component(FileBrowser.name, FileBrowser)
