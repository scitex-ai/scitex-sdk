#!/usr/bin/env python3
"""EmptyState component metadata."""

from .._registry import register_component


class EmptyState:
    """The "nothing here" block, once — in two scales.

    THE MOST DUPLICATED SHAPE IN THE FLEET. Measured 2026-07-28 across every
    app's own CSS: scitex-cards 22 classes, figrecipe 16, scitex-writer 6,
    scitex-scholar 2 — and scitex-sdk ui itself carried ~20 more, every one welded
    to a host component (combobox, miller, recent-pane, chat, viewer,
    repo-monitor, worktree-tree...). Base had empties but no empty, and base
    was the largest single offender.

    Two scales, because the instances split cleanly and a primitive covering
    only the large one could not absorb base's own inline cases:

    * default — full panel: icon + title + hint + optional action, centred.
      Derived from figrecipe's ``.datatable-empty-*``, the fullest existing
      implementation.
    * ``--compact`` — a single muted line for dropdowns and narrow panes.
      Derived from base's own ``combobox__empty`` / ``recent-pane__empty``.

    ``title`` is required: an empty state with no words is a blank area, and a
    blank area is indistinguishable from a load that failed — the one thing an
    empty state exists to rule out.

    TS:  scitex_sdk/ui/ts/app/empty/index
    CSS: scitex_sdk/ui/css/app/empty.css
    """

    name = "empty-state"
    version = "0.1.0"
    description = (
        "Empty-state block in two scales — full panel with icon/title/hint/action, "
        "and a compact single line for dropdowns"
    )
    ts_entry = "scitex_sdk/ui/ts/app/empty/index"
    css_file = "scitex_sdk/ui/css/app/empty.css"


register_component(EmptyState.name, EmptyState)
