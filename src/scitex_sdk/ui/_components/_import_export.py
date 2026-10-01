#!/usr/bin/env python3
"""Import/export component metadata."""

from .._registry import register_component


class ImportExport:
    """The standard import/export pattern (compass L623).

    A trigger opens a panel of FORMAT OPTIONS (BibTeX, RIS, CSL JSON,
    Zotero, Markdown, PDF, ...); picking one shows a confirm bar;
    confirming emits ``stx-import-export:confirm`` (bubbles, detail
    ``{direction, formatId, formatLabel}``) and the consuming app
    performs the transfer.

    The component owns the pattern — the markup, the BEM vocabulary, the
    confirm/cancel flow, and the event contract. It does NOT own the data
    (which formats exist is the app's) or the bytes (reading a file,
    writing a citation file). The confirm/cancel bar uses the standard
    ``.stx-button`` (form-controls) rather than re-defining buttons.

    The confirm step exists because a format list is long enough that an
    accidental tap on "Zotero" should not immediately fire a transfer.

    CSS: scitex_sdk/ui/css/app/import-export.css
    """

    name = "import-export"
    version = "0.1.0"
    description = (
        "Standard import/export pattern: format list + confirm/cancel "
        "bar, emits stx-import-export:confirm"
    )
    ts_entry = "scitex_sdk/ui/ts/app/import-export/index"
    css_file = "scitex_sdk/ui/css/app/import-export.css"
    # Pre-built ES-module sibling for consumers without a bundler step: a
    # browser executes the .js module directly where it cannot execute the
    # .ts. Mirrors the TS API (same exports). Rebuild command is in the
    # file banner.
    js_file = "scitex_sdk/ui/js/app/import-export.js"


register_component(ImportExport.name, ImportExport)
