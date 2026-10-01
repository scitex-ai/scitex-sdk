#!/usr/bin/env python3
"""Form controls component metadata."""

from .._registry import register_component


class FormControls:
    """The single definition of input / select / textarea / checkbox / button,
    including the standard control heights (--input-height / --button-height).

    Harvested from scitex-cards, which redefines the same controls in at least
    SEVEN places (``body select``, ``.tl-ctl select``, ``.filt-sort select``,
    ``.filt-groupby select``, ``.details-row--filter select``, ``.card-select``,
    ``.at-select``) with two incompatible visual languages live at once:

        base  : 4px radius, 0.82rem, purple focus, tokenised background
        .at-* : 6px radius, 0.92rem, green  focus, background hard-coded #232a36

    A control's appearance should not depend on which toolbar it sits in.

    The hard-coded background is not a live bug today — board_v3 defines
    ``--text`` once and ships no light-mode block, despite its own file header
    claiming "dark/light mode". It becomes one the moment a light theme lands:
    themed text on an unthemed dark box. Every colour here is a token, so that
    class of failure cannot occur.

    Invalid state is driven by ``aria-invalid``, never by a class, so the
    visual state cannot drift from what assistive tech is told — a red border
    with no ``aria-invalid`` is a lie to a screen reader.

    The checkbox is a real ``<input type=checkbox>`` themed with
    ``accent-color`` rather than the usual hidden-input-plus-styled-span, so
    keyboard behaviour, the indeterminate state and AT semantics stay intact.

    CSS-only: no TypeScript entry. Native controls already have behaviour; the
    problem being solved is that they had SIX appearances.

    CSS: scitex_sdk/ui/css/app/form-controls.css
    """

    name = "form-controls"
    version = "0.1.0"
    description = "Single definition of input/select/textarea/checkbox/button styling with standard control heights"
    ts_entry = None  # CSS-only component
    css_file = "scitex_sdk/ui/css/app/form-controls.css"


register_component(FormControls.name, FormControls)
