#!/usr/bin/env python3
"""MediaViewer component metadata."""

from .._registry import register_component


class MediaViewer:
    name = "media-viewer"
    version = "0.1.0"
    description = "Display images, PDFs, and diagrams with zoom/pan"
    ts_entry = "scitex_sdk/ui/ts/app/media-viewer/index"
    css_file = "scitex_sdk/ui/css/app/media-viewer.css"


register_component(MediaViewer.name, MediaViewer)
