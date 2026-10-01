#!/usr/bin/env python3
"""ElementInspector component metadata."""

from .._registry import register_component


class ElementInspector:
    """Visual DOM debugging overlay toggled with Alt+I.

    Highlights every HTML element with colored rectangles and labels,
    supports rectangle selection (Ctrl+Alt+I), batched scanning
    (Ctrl+I), and a debug snapshot (Ctrl+Shift+I). Intended for
    developer/QA use and gated behind DEBUG/staff via
    ``scitex_sdk.ui.context_processors.element_inspector``.

    Include in a page with::

        {% include "scitex_sdk/ui/_element_inspector.html" %}

    TypeScript entry: scitex_sdk/ui/ts/utils/element-inspector.ts
    Bundled JS: scitex_sdk/ui/js/utils/element-inspector.js
    CSS: scitex_sdk/ui/css/utils/element-inspector.css
    """

    name = "element-inspector"
    version = "0.1.0"
    description = "Visual DOM debugging overlay toggled with Alt+I"
    ts_entry = "scitex_sdk/ui/ts/utils/element-inspector"
    css_file = "scitex_sdk/ui/css/utils/element-inspector.css"


register_component(ElementInspector.name, ElementInspector)
