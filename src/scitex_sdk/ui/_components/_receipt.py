#!/usr/bin/env python3
"""Receipt component metadata."""

from .._registry import register_component


class Receipt:
    """Delivery receipt: one mark that advances through its delivery states.

    The claude-code-telegrammer model — a single mark that ADVANCES, not a row
    of indicators. Built base-first at scitex-cards' request so their chat
    never grows a private one.

    Four states, and ``unknown`` is the default: ``unknown`` (no signal yet),
    ``sent`` (reached the store), ``seen`` (reached the recipient), ``failed``
    (delivery known dead). A read/unread boolean cannot express "we do not
    know", and collapsing that into either pole reports undelivered messages as
    delivered. Setting an unrecognised state raises rather than falling back to
    ``unknown``, which would hide a failure behind "no signal yet".

    TS:  scitex_sdk/ui/ts/app/receipt/index
    CSS: scitex_sdk/ui/css/app/receipt.css
    """

    name = "receipt"
    version = "0.1.0"
    description = (
        "Delivery receipt mark advancing through unknown / sent / seen / failed"
    )
    ts_entry = "scitex_sdk/ui/ts/app/receipt/index"
    css_file = "scitex_sdk/ui/css/app/receipt.css"


register_component(Receipt.name, Receipt)
