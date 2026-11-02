"""Native document-section navigation component metadata."""

from .._registry import register_component


class SectionNav:
    """Native anchor navigation with passive current-section tracking."""

    name = "section-nav"
    version = "0.1.0"
    description = "Native section anchors with shared underline and aria-current tracking"
    ts_entry = "scitex_sdk/ui/ts/app/section-nav/index"
    css_file = "scitex_sdk/ui/css/app/content-tabs.css"
    js_file = "scitex_sdk/ui/js/app/section-nav.js"


register_component(SectionNav.name, SectionNav)
