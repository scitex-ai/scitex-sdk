#!/usr/bin/env python3
"""ReplyQuote component metadata."""

from .._registry import register_component


class ReplyQuote:
    """Truncated, clickable quote of the message being replied to.

    Built base-first at scitex-cards' request so the chat never grows a
    private one. Activating it scrolls to the original and flashes it.

    Colour-agnostic by construction: it sits inside a bubble that is already
    colour-coded by sender, so the stylesheet derives its tint, accent bar and
    focus ring from ``currentColor`` rather than choosing its own. Drop it into
    any bubble and it takes that bubble's colour, with nothing to configure
    per sender.

    A quote whose original cannot be reached renders ORPHANED — visibly inert
    — instead of staying clickable and silently doing nothing.

    TS:  scitex_sdk/ui/ts/app/reply-quote/index
    CSS: scitex_sdk/ui/css/app/reply-quote.css
    """

    name = "reply-quote"
    version = "0.1.0"
    description = (
        "Truncated clickable quote of a replied-to message, inheriting its "
        "bubble's colour"
    )
    ts_entry = "scitex_sdk/ui/ts/app/reply-quote/index"
    css_file = "scitex_sdk/ui/css/app/reply-quote.css"


register_component(ReplyQuote.name, ReplyQuote)
