#!/usr/bin/env python3
"""Monaco Editor component metadata."""

from .._registry import register_component


class MonacoEditor:
    name = "monaco-editor"
    version = "0.1.0"
    description = "Monaco code editor with diff support, themes, and language detection"
    ts_entry = "scitex_sdk/ui/ts/app/monaco-editor/index"
    css_file = None  # Monaco CSS imported via JS


register_component(MonacoEditor.name, MonacoEditor)
