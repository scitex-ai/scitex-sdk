#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._toast."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._toast import Toast

_STATIC = package_dir() / "static"
_TONES = ("info", "success", "error")


def _strip_comments(text: str) -> str:
    """Drop /* … */ and // … so a guard cannot match its own prose.

    Every claim below is about a DECLARATION. Without this, a test asserting
    that a token is used passes on the comment that merely names the token.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


class TestToast:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Toast) is Toast

    def test_ships_both_styling_and_behaviour(self):
        # Arrange
        # Act
        # Assert
        assert Toast.ts_entry and Toast.css_file, (
            "a toast with CSS but no behaviour leaves every adopter writing "
            "the show/hide timing themselves, which is what this replaces"
        )


class TestToneSurvivesInBothLayers:
    """A tone the stylesheet does not know renders as the default colour.

    An error message wearing the neutral background is worse than no toast:
    it reports a failure in the visual language of success.
    """

    def _css(self) -> str:
        return _strip_comments((_STATIC / Toast.css_file).read_text())

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/toast"
        return _strip_comments("\n".join(p.read_text() for p in root.glob("*.ts")))

    @pytest.mark.parametrize("tone", _TONES)
    def test_tone_is_declared_in_the_module(self, tone):
        # Arrange
        ts = self._ts()

        # Act
        declared = re.search(rf'"{tone}"', ts)

        # Assert
        assert declared, f"{tone} is unreachable from the module"

    @pytest.mark.parametrize("tone", ("success", "error"))
    def test_non_default_tone_has_its_own_background(self, tone):
        # Arrange — info is the element's base background, so only the two
        # tones that must OVERRIDE it need a selector of their own.
        css = self._css()

        # Act
        styled = re.search(rf'\[data-tone="{tone}"\]', css)

        # Assert
        assert styled, (
            f"{tone} has no background rule, so it renders in the neutral "
            "colour — an error message that looks like a success"
        )


class TestHarvestedDefectsStayFixed:
    """The three bugs carried by the source this was harvested from.

    Each is cheap to reintroduce by editing for tidiness, and none of them is
    visible in a screenshot — which is why they are asserted rather than
    trusted to review.
    """

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/toast"
        return _strip_comments("\n".join(p.read_text() for p in root.glob("*.ts")))

    def test_pending_hide_timer_is_cancelled(self):
        # Arrange — the original scheduled a bare setTimeout per message and
        # never cleared it, so message N's timer hid message N+1 early.
        ts = self._ts()

        # Act
        cancels = re.search(r"clearTimeout\(", ts)

        # Assert
        assert cancels, (
            "no clearTimeout: two toasts in quick succession will let the "
            "first message's timer hide the second one early"
        )

    def test_undo_button_is_disabled_while_the_handler_runs(self):
        # Arrange
        ts = self._ts()

        # Act
        disables = re.search(r"\.disabled\s*=\s*true", ts)

        # Assert
        assert disables, (
            "an async undo that is not disabled on click can be fired twice "
            "by an impatient second click"
        )

    def test_message_text_is_never_written_as_html(self):
        # Arrange — toasts carry server errors and user-supplied names.
        ts = self._ts()

        # Act
        uses_inner_html = re.search(r"\.innerHTML", ts)

        # Assert
        assert not uses_inner_html, (
            "innerHTML in a toast is an injection site; the message must be "
            "set with textContent"
        )

    def test_no_parameter_shadows_the_global_window(self):
        # Arrange — the source's `toastUndo(msg, undoFn, window)` shadowed the
        # global inside its body; it survived only because nothing read it.
        ts = self._ts()

        # Act
        shadows = re.search(r"\(\s*[^)]*\bwindow\s*[:,)]", ts)

        # Assert
        assert not shadows, "a parameter named `window` shadows the global"


class TestUndoStyleIsDeclaredExactlyOnce:
    """The source defined `.toast-undo` in two stylesheets.

    03-right-and-modal.css and 04-collapse-and-groups.css both declared it, so
    the live button was a load-order merge nobody had written on purpose.
    Collapsing it is the point of harvesting; a second block here would
    recreate the same ambiguity inside one file.
    """

    def test_undo_selector_appears_once(self):
        # Arrange
        css = _strip_comments((_STATIC / Toast.css_file).read_text())

        # Act
        blocks = re.findall(r"^\.stx-toast__undo\s*\{", css, flags=re.MULTILINE)

        # Assert
        assert len(blocks) == 1, (
            f"{len(blocks)} base declarations of .stx-toast__undo — the "
            "duplicate this harvest exists to collapse"
        )


class TestReducedMotionIsHonoured:
    def test_transform_travel_is_dropped_for_reduced_motion(self):
        # Arrange
        css = _strip_comments((_STATIC / Toast.css_file).read_text())

        # Act
        honoured = re.search(r"prefers-reduced-motion:\s*reduce", css)

        # Assert
        assert honoured, (
            "the toast slides in; a user who asked for reduced motion should "
            "still get the message, just not the travel"
        )
