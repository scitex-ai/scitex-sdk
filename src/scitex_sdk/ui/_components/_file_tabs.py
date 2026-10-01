#!/usr/bin/env python3
"""FileTabs component metadata."""

from .._registry import register_component


class FileTabs:
    name = "file-tabs"
    version = "0.1.0"
    description = "Tab bar for managing open files with drag-reorder and rename"
    ts_entry = "scitex_sdk/ui/ts/app/file-tabs/index"
    css_file = "scitex_sdk/ui/css/app/file-tabs.css"


register_component(FileTabs.name, FileTabs)
