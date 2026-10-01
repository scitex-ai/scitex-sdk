#!/usr/bin/env python3
"""Toast component metadata."""

from .._registry import register_component


class Toast:
    """Transient notification with an optional undo.

    Harvested from scitex-cards' board_v3 ``toast()`` / ``toastUndo()`` so no
    consumer has to keep a private copy. Three defects in that source are fixed
    here rather than carried across:

    - Auto-hide timers were never cancelled, so two messages in quick
      succession meant the FIRST message's timer hid the SECOND one early.
    - ``toastUndo(msg, undoFn, window)`` named its third parameter ``window``,
      shadowing the global inside the body.
    - It required a hand-placed ``#toast`` div and dereferenced the lookup
      without a null check, so a page missing that element threw on the first
      notification. This owns its element instead.

    The undo button disables itself while an async handler is in flight, so an
    impatient second click cannot fire it twice, and the toast hides whether
    the undo resolved or threw — leaving it up after a failed undo would imply
    the action is still reversible.

    ``.toast-undo`` was defined TWICE in the source (03-right-and-modal.css and
    04-collapse-and-groups.css), making the live button a load-order merge of
    the two. Collapsed into one definition that keeps whichever declaration was
    winning, so adopting this is not a silent restyle.

    TS:  scitex_sdk/ui/ts/app/toast/index
    CSS: scitex_sdk/ui/css/app/toast.css
    """

    name = "toast"
    version = "0.1.0"
    description = "Transient notification with an optional time-boxed undo"
    ts_entry = "scitex_sdk/ui/ts/app/toast/index"
    css_file = "scitex_sdk/ui/css/app/toast.css"


register_component(Toast.name, Toast)
