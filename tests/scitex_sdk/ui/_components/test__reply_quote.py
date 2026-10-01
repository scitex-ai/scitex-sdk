#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._reply_quote."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._reply_quote import ReplyQuote

_STATIC = package_dir() / "static"


class TestReplyQuote:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ReplyQuote) is ReplyQuote

    def test_ships_both_styling_and_behaviour(self):
        # Arrange
        # Act
        # Assert
        assert ReplyQuote.ts_entry and ReplyQuote.css_file, (
            "the scroll-to-original behaviour is the point; CSS alone would "
            "leave every adopter reimplementing it"
        )


class TestColourAgnostic:
    """It sits inside a bubble already coloured by sender, so it must inherit.

    scitex-cards' stated constraint. A hardcoded background or text colour
    would be correct on exactly one bubble type and wrong on every other, and
    the wrongness is silent — it just looks slightly off for one sender.
    """

    def _css(self) -> str:
        return (_STATIC / ReplyQuote.css_file).read_text()

    def test_no_hardcoded_hex_colours(self):
        # Arrange
        css = self._css()
        # Act
        hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
        # Assert
        assert not hexes, (
            f"hardcoded colours {hexes} would override the bubble's own palette; "
            f"derive from currentColor instead"
        )

    def test_derives_from_current_color(self):
        # Arrange
        css = self._css()
        # Act
        derived = css.count("currentColor")
        # Assert
        assert derived >= 3, (
            f"only {derived} currentColor references; the tint, accent bar and "
            f"focus ring must all inherit or the quote will clash with some "
            f"sender's bubble"
        )

    def test_text_is_clamped(self):
        # Arrange
        css = self._css()
        # Act
        clamped = "-webkit-line-clamp" in css
        # Assert
        assert clamped, (
            "an unclamped quote grows with the quoted message, letting one long "
            "message push every reply off screen"
        )

    def test_reduced_motion_is_respected(self):
        # Arrange
        css = self._css()
        # Act
        respected = "prefers-reduced-motion" in css
        # Assert
        assert respected, "the jump-to-original flash must honour reduced motion"


class TestOrphanedStateExists:
    """A dead link that looks alive reports success it has not verified.

    Same failure shape as a receipt that cannot say "unknown": the quote would
    stay clickable and silently do nothing when the original is gone.
    """

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/reply-quote"
        return "\n".join(p.read_text() for p in root.glob("*.ts"))

    def test_module_can_mark_orphaned(self):
        # Arrange
        ts = self._ts()
        # Act
        marks = "stx-app-reply-quote--orphaned" in ts
        # Assert
        assert marks, "the module never marks a quote orphaned"

    def test_orphaned_state_is_styled(self):
        # Arrange
        css = (_STATIC / ReplyQuote.css_file).read_text()
        # Act
        styled = ".stx-app-reply-quote--orphaned" in css
        # Assert
        assert styled, (
            "orphaned renders identically to live; the user cannot tell the "
            "original is gone until they click and nothing happens"
        )

    def test_unreachable_original_disables_the_control(self):
        # Arrange
        ts = self._ts()
        # Act
        disabled = re.search(r"\.disabled\s*=\s*true", ts) is not None
        # Assert
        assert disabled, (
            "an orphaned quote must be genuinely inert, not merely dimmed — "
            "styling alone still accepts the click"
        )


class TestStylesheetReachesThePage:
    """0.11.1 shipped badge.css importable by nothing; do not repeat it."""

    @pytest.mark.parametrize("bundle", ["app.css", "all.css"])
    def test_bundle_imports_the_stylesheet(self, bundle):
        # Arrange
        text = (_STATIC / "scitex_sdk/ui/css" / bundle).read_text()
        # Act
        imported = "./app/reply-quote.css" in text
        # Assert
        assert imported, (
            f"{bundle} does not import app/reply-quote.css; adopters would get "
            f"the class names and no styling. Regenerate: npx tsx css/_build-index.ts"
        )


# EOF
