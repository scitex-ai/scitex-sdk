#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._drawer."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._drawer import Drawer

_STATIC = package_dir() / "static"
_SIDES = ("left", "right")


def _strip_comments(text: str) -> str:
    """Drop /* … */ and // … so a guard cannot match its own prose."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def _ts() -> str:
    root = _STATIC / "scitex_sdk/ui/ts/app/drawer"
    return _strip_comments("\n".join(p.read_text() for p in root.glob("*.ts")))


def _css() -> str:
    return _strip_comments((_STATIC / Drawer.css_file).read_text())


class TestDrawer:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Drawer) is Drawer

    def test_ships_both_styling_and_behaviour(self):
        # Arrange
        # Act
        # Assert
        assert Drawer.ts_entry and Drawer.css_file, (
            "a drawer with CSS but no behaviour leaves adopters writing the "
            "focus and escape handling themselves, which is what this replaces"
        )


class TestClosedDrawerIsUnreachable:
    """The defect this component exists to fix.

    The harvested source hid the closed panel with `transform` alone. A
    transform moves pixels and nothing else, so the panel kept its place in the
    tab order and the accessibility tree: tabbing walked focus into an
    invisible drawer with no visible ring, and the next Enter activated a link
    the user could not see.

    `inert` (keyboard + AT) and `visibility` (pointer) are independent — one
    does not imply the other, so both are asserted.
    """

    def test_closed_panel_is_marked_inert(self):
        # Arrange
        ts = _ts()

        # Act
        sets_inert = re.search(r'toggleAttribute\(\s*"inert"', ts)

        # Assert
        assert sets_inert, (
            "without inert, a closed drawer is off-screen but still tabbable "
            "and focus disappears into it"
        )

    def test_closed_panel_is_hidden_from_hit_testing(self):
        # Arrange
        css = _css()

        # Act
        hides = re.search(r"visibility:\s*hidden", css)

        # Assert
        assert hides, (
            "a transform-only hide leaves the closed panel clickable where it "
            "sits off-screen"
        )

    def test_transform_alone_is_not_the_only_hiding_mechanism(self):
        # Arrange — the whole point: the source had the transform and nothing
        # else, and looked correct in a screenshot.
        css = _css()

        # Act
        has_transform = re.search(r"transform:\s*translateX", css)
        has_visibility = re.search(r"visibility:\s*hidden", css)

        # Assert
        assert has_transform and has_visibility, (
            "the transform is the animation, not the hiding; both must exist"
        )


class TestKeyboardCompleteness:
    def test_escape_key_closes_the_drawer(self):
        # Arrange
        ts = _ts()

        # Act
        handles_escape = re.search(r'key\s*===\s*"Escape"', ts)

        # Assert
        assert handles_escape, (
            "an overlay openable by keyboard but closable only by pointer is "
            "a trap on any device with a keyboard"
        )

    def test_tab_is_trapped_while_open(self):
        # Arrange
        ts = _ts()

        # Act
        traps = re.search(r'key\s*===\s*"Tab"', ts)

        # Assert
        assert traps, "Tab must not leave an open drawer for the page behind"

    def test_focus_is_restored_on_close(self):
        # Arrange — closing while focus sits on a now-inert element strands it.
        ts = _ts()

        # Act
        restores = re.search(r"restoreFocus", ts)

        # Assert
        assert restores, "focus must return to where it came from"

    def test_trigger_announces_its_state(self):
        # Arrange
        ts = _ts()

        # Act
        announces = re.search(r'"aria-expanded"', ts)

        # Assert
        assert announces, "the trigger must say whether the drawer is open"


class TestSingleSourceOfTruth:
    """Panel and scrim were toggled independently in the source.

    Two separate `classList.toggle("open")` calls on two elements desynchronise
    as soon as any path clears one without the other — and `closeDrawer()` was
    called from elsewhere in that file. Once desynchronised, ONE click puts
    them in opposite states: a scrim with no drawer, or a drawer with no scrim
    to dismiss it.
    """

    def test_open_state_is_held_in_one_place(self):
        # Arrange
        ts = _ts()

        # Act
        declares_state = re.search(r"private\s+isOpen\s*=\s*false", ts)

        # Assert
        assert declares_state, "one boolean must own the open state"

    def test_no_bare_toggle_of_the_open_class(self):
        # Arrange — a bare toggle() flips whatever is there, which is how the
        # two elements diverge; both must be SET from the boolean instead.
        ts = _ts()

        # Act
        bare_toggles = re.findall(
            r'classList\.toggle\(\s*"[^"]*(?:--open|\bopen)"\s*\)', ts
        )

        # Assert
        assert not bare_toggles, (
            f"{len(bare_toggles)} bare open-class toggle(s); pass the state "
            "explicitly as the second argument so both elements are derived "
            "from one boolean"
        )


@pytest.mark.parametrize("side", _SIDES)
def test_each_side_has_a_slide_direction(side):
    # Arrange
    css = _css()

    # Act
    styled = re.search(rf'\[data-side="{side}"\]', css)

    # Assert
    assert styled, f"a {side} drawer has no off-screen position to slide from"


def test_scroll_lock_class_is_defined():
    # Arrange — on a phone, dragging over an open drawer otherwise scrolls the
    # page underneath it.
    css = _css()

    # Act
    defined = re.search(r"\.stx-drawer-scroll-locked", css)

    # Assert
    assert defined, "the module adds this class to <body>; it must do something"


def test_reduced_motion_is_honoured():
    # Arrange
    css = _css()

    # Act
    honoured = re.search(r"prefers-reduced-motion:\s*reduce", css)

    # Assert
    assert honoured, "the drawer slides; that travel should be optional"
