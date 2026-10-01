#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._attachment."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._attachment import Attachment

_STATIC = package_dir() / "static"


def _rules_only(css: str) -> str:
    """CSS with comments stripped.

    The header documents scitex-cards' original `.msg .att-img` selectors, so a
    naive substring search finds the prose and reports a scoping that does not
    exist. Caught by this guard failing on its own first run: a check that reads
    comments is measuring what we wrote about the code, not the code.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


class TestAttachment:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Attachment) is Attachment


class TestHarvestedRulesSurvive:
    """These two rules were paid for in real bugs on scitex-cards' side.

    Both look like arbitrary values a tidy-up would "simplify", which is
    exactly why they are pinned: the bugs they fix are invisible until someone
    opens the page on a phone or attaches a long filename.
    """

    def _css(self) -> str:
        return (_STATIC / Attachment.css_file).read_text()

    def test_image_cap_is_responsive_not_fixed(self):
        # Arrange
        css = self._css()
        # Act
        responsive = "min(360px, 100%)" in css
        # Assert
        assert responsive, (
            "a bare 360px max-width overflows a phone bubble, which is narrower "
            "than 360 — scitex-cards hit this and min() is the fix"
        )

    def test_long_filenames_cannot_blow_out_the_column(self):
        # Arrange
        css = self._css()
        # Act
        broken = "word-break: break-all" in css
        # Assert
        assert broken, (
            "filenames are frequently one long unbroken token; without this the "
            "chip widens the whole column"
        )

    def test_primitive_is_not_scoped_to_a_container(self):
        # Arrange
        # Comments stripped: the header quotes their `.msg .att-img` selectors,
        # and matching prose would report a scoping the rules do not have.
        rules = _rules_only(self._css())
        # Act
        scoped = ".msg" in rules
        # Assert
        assert not scoped, "the primitive must not require a `.msg` ancestor"


class TestMarkupContractPreserved:
    """Their adoption should be a deletion, so the emitted markup must match."""

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/attachment"
        return "\n".join(p.read_text() for p in root.glob("*.ts"))

    def test_images_are_lazy(self):
        # Arrange
        ts = self._ts()
        # Act
        lazy = 'loading = "lazy"' in ts
        # Assert
        assert lazy, (
            "attachments sit in a scrolling transcript; eager loading fetches "
            "every image in the history"
        )

    def test_links_are_safe_new_tab(self):
        # Arrange
        ts = self._ts()
        # Act
        safe = ts.count('rel = "noopener"')
        # Assert
        assert safe >= 2, (
            f"only {safe} noopener assignments; a target=_blank link without it "
            f"hands the opener to the linked page"
        )

    def test_paperclip_stays_a_text_prefix_by_default(self):
        # Arrange
        # Match the CONSTANT, not any occurrence of the emoji: it also appears
        # in two docstrings, so a substring search stayed green even after the
        # prefix was emptied. Mutation probe E caught that — a guard reading
        # documentation measures what we wrote about the code, not the code.
        ts = self._ts()
        # Act
        declared = re.search(r'PAPERCLIP_PREFIX\s*=\s*"📎 "', ts) is not None
        # Assert
        assert declared, (
            "the paperclip is a literal text prefix in scitex-cards' contract, "
            "not a pseudo-element; changing it silently breaks anyone matching "
            "on text content"
        )


class TestStylesheetReachesThePage:
    """0.11.1 shipped badge.css importable by nothing; do not repeat it."""

    @pytest.mark.parametrize("bundle", ["app.css", "all.css"])
    def test_bundle_imports_the_stylesheet(self, bundle):
        # Arrange
        text = (_STATIC / "scitex_sdk/ui/css" / bundle).read_text()
        # Act
        imported = "./app/attachment.css" in text
        # Assert
        assert imported, (
            f"{bundle} does not import app/attachment.css; adopters would get "
            f"the class names and no styling. Regenerate: npx tsx css/_build-index.ts"
        )


# EOF
