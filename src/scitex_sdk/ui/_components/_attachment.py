#!/usr/bin/env python3
"""Attachment component metadata."""

from .._registry import register_component


class Attachment:
    """Inline attachment chips: a lazy image and a file link.

    HARVESTED from scitex-cards rather than designed here — they shipped these
    first and sent the rules verbatim, so their adoption is a deletion instead
    of a visual regression.

    PRESENTATION ONLY. Base owns no part of the storage path: attachments are
    moving into a cards.db table on their side, and encoding the interim
    convention here would bake in a plumbing decision that is theirs and
    already changing.

    Two rules are load-bearing and preserved exactly, each paid for in a real
    bug: ``min(360px, 100%)`` rather than a bare 360px, because a phone bubble
    is narrower than 360 and a fixed cap overflowed it; and
    ``word-break: break-all`` on the file chip, because filenames are often one
    long unbroken token that blew out the column width.

    TS:  scitex_sdk/ui/ts/app/attachment/index
    CSS: scitex_sdk/ui/css/app/attachment.css
    """

    name = "attachment"
    version = "0.1.0"
    description = (
        "Inline attachment chips — lazy-loaded image and file link, sized for "
        "narrow bubbles"
    )
    ts_entry = "scitex_sdk/ui/ts/app/attachment/index"
    css_file = "scitex_sdk/ui/css/app/attachment.css"


register_component(Attachment.name, Attachment)
