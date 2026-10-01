#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._empty."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._empty import EmptyState

_STATIC = package_dir() / "static"


def _rules_only(css: str) -> str:
    """CSS with comments stripped — a guard must read rules, not prose."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


class TestEmptyState:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(EmptyState) is EmptyState


class TestBothScalesExist:
    """The instances split in two, and covering only one absorbs neither set.

    Base's own ~20 welded empties are INLINE affordances (combobox dropdown,
    recent-pane) — a 60px-padded panel block cannot replace them. figrecipe's
    and cards' are full-panel states. A primitive missing either scale leaves
    that whole population unable to adopt.
    """

    def _css(self) -> str:
        return _rules_only((_STATIC / EmptyState.css_file).read_text())

    def test_full_panel_scale_exists(self):
        # Arrange
        css = self._css()
        # Act
        parts = [
            p
            for p in ("__icon", "__title", "__hint", "__action")
            if f".stx-app-empty{p}" in css
        ]
        # Assert
        assert len(parts) == 4, (
            f"full-panel scale only defines {parts}; icon/title/hint/action is "
            f"the shape figrecipe and cards both converged on"
        )

    def test_compact_scale_exists(self):
        # Arrange
        css = self._css()
        # Act
        compact = ".stx-app-empty--compact" in css
        # Assert
        assert compact, (
            "without a compact scale, base's own inline empties (combobox, "
            "recent-pane) cannot adopt this and stay welded"
        )

    def test_compact_suppresses_the_panel_only_parts(self):
        # Arrange
        css = self._css()
        # Act
        # icon and action are panel furniture; leaving them visible inline
        # would push a dropdown open by 36px of glyph.
        suppressed = re.search(
            r"\.stx-app-empty--compact\s+\.stx-app-empty__icon[^{]*\{[^}]*display:\s*none",
            css,
        )
        # Assert
        assert suppressed, "compact must hide the icon slot"


class TestTitleIsRequired:
    """A wordless empty state is indistinguishable from a failed load."""

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/empty"
        return "\n".join(p.read_text() for p in root.glob("*.ts"))

    def test_title_is_not_optional_in_the_type(self):
        # Arrange
        ts = self._ts()
        # Act
        optional = re.search(r"\btitle\?\s*:", ts) is not None
        # Assert
        assert not optional, (
            "title must stay required; an empty state with no words is a blank "
            "area, and a blank area reads as a load that failed"
        )

    def test_state_is_announced(self):
        # Arrange
        ts = self._ts()
        # Act
        announced = 'role", "status"' in ts or "role\", \"status\"" in ts
        # Assert
        assert announced, (
            "the block carries the only signal that the surface is empty on "
            "purpose; a screen reader must not skip it"
        )


class TestStylesheetReachesThePage:
    """0.11.1 shipped badge.css importable by nothing; do not repeat it."""

    @pytest.mark.parametrize("bundle", ["app.css", "all.css"])
    def test_bundle_imports_the_stylesheet(self, bundle):
        # Arrange
        text = (_STATIC / "scitex_sdk/ui/css" / bundle).read_text()
        # Act
        imported = "./app/empty.css" in text
        # Assert
        assert imported, (
            f"{bundle} does not import app/empty.css; adopters would get the "
            f"class names and no styling. Regenerate: npx tsx css/_build-index.ts"
        )


# EOF
