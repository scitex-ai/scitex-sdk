#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._app_launcher (compass L624).

The Python half is a registry metadata object, so ``check_metadata`` covers
its shape. The behaviour half lives in the TypeScript module and its esbuild
bundle; this repo has no JS test runner, so it is verified statically — the
same approach as ``test__context_menu.py`` and ``test__import_export.py``.
The DOM regression test lives in ``tests/scitex_sdk/ui/ts/app-launcher.render.test.ts``
and is run directly by Node, not pytest.
"""

import re

import pytest

from scitex_sdk import ui as scitex_ui  # noqa: F401  (import registers every component)
from tests._checkout import package_dir
from tests.develop.test_rendered_classes_have_styles import _covered
from scitex_sdk.ui._components._app_launcher import AppLauncher

_STATIC = package_dir() / "static"

_CLS = "stx-app-launcher"
_SELECT_EVENT = "stx-app-launcher:select"


def _ts_text() -> str:
    root = _STATIC / "scitex_sdk/ui/ts/app/app-launcher"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.glob("*.ts")))


def _css_text() -> str:
    return (_STATIC / AppLauncher.css_file).read_text(encoding="utf-8")


def _bundle_text() -> str:
    return (_STATIC / AppLauncher.js_file).read_text(encoding="utf-8")


def _emitted_classes() -> set[str]:
    """Every BEM class the module writes.

    Multi-class template literals (e.g. ```${CLS}__tile ${CLS}__tile--current```)
    are handled by splitting on whitespace and keeping only ``__``/``--`` tokens,
    which recovers the true emitted population. The shared class-manifest
    grammar (_BUILT/_ELEMENT in test_class_manifest_matches_source) stops at the
    first non-name token and so records neither ``__tile`` nor ``__tile--current``
    in one shot (the manifest is a declared LOWER_BOUND, which is in-contract);
    this test documents the fuller set rather than patching a shared guard.
    """
    emitted = {_CLS}
    for group in re.findall(r"\$\{CLS\}([^`]*)", _ts_text()):
        for tok in group.split():
            if tok.startswith("__") or tok.startswith("--"):
                emitted.add(_CLS + tok)
    return emitted


class TestAppLauncher:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(AppLauncher) is AppLauncher

    def test_ships_behaviour_not_only_styling(self):
        # Arrange
        # Act
        entry = AppLauncher.ts_entry
        # Assert
        assert entry == "scitex_sdk/ui/ts/app/app-launcher/index", (
            "the TS entry declares the pattern's mechanics (trigger, grid of "
            "tiles, select event); without it list_components() reveals "
            "styling with no behaviour and every adopter re-implements it"
        )

    def test_select_event_is_an_exported_constant(self):
        # Arrange
        ts = _ts_text()
        # Act
        exported = f'export const APP_LAUNCHER_SELECT = "{_SELECT_EVENT}"' in ts
        # Assert
        assert exported, (
            "the select event name is the wire contract apps listen on; it "
            "must be an exported constant, not a string buried in a handler"
        )

    def test_tiles_are_real_buttons_not_divs(self):
        # Arrange
        ts = _ts_text()
        # Act
        # The tile creation line must use createElement("button"), not "div"
        tile_is_button = re.search(
            r'tile\s*=\s*document\.createElement\("button"\)', ts
        ) is not None
        # Assert
        assert tile_is_button, (
            "tiles must be real <button> elements: platform keyboard operability "
            "(Tab, Enter, Space) comes for free — a <div> tile would need a "
            "hand-rolled key handler and fail WCAG 2.1.1 non-text contrast"
        )


class TestMarkupMatchesStylesheet:
    """The module builds DOM by hand; a CSS rename would silently orphan it.

    Reused from the repo drift-guard (_covered) rather than re-decided here.
    """

    def test_every_emitted_class_is_styled(self):
        # Arrange
        emitted = _emitted_classes()
        styled = set(re.findall(r"\.([\w][\w-]*)", _css_text()))
        # Act
        unstyled = sorted(c for c in emitted if not _covered(c, styled))
        # Assert
        assert not unstyled, (
            f"emitted by the module but no stylesheet rule reaches them "
            f"(block-level coverage accepted, per the repo drift guard): "
            f"{unstyled}"
        )

    def test_the_class_set_is_not_vacuous(self):
        # Arrange
        # Act
        emitted = _emitted_classes()
        # Assert
        assert len(emitted) >= 10, (
            f"only {sorted(emitted)} — the extraction regex stopped matching "
            f"the ${{CLS}} template literals; this guard would pass no matter "
            f"what the module emitted"
        )

    def test_tile_has_44px_min_height_for_touch(self):
        # Arrange
        css = _css_text()
        # Act
        has_min_height = re.search(
            r"\.stx-app-launcher__tile\s*\{[^}]*min-height:\s*44px", css
        ) is not None
        # Assert
        assert has_min_height, (
            "the tile must carry min-height: 44px — WCAG 2.5.5 touch target "
            "minimum, and the same rule that .stx-shell-launcher-link already "
            "enforces. A tile that shrinks below 44px on mobile is "
            "inaccessible, not just inconvenient."
        )

    def test_grid_glyph_is_rendered_in_the_trigger(self):
        # Arrange
        ts = _ts_text()
        # Act
        has_glyph = "\u7530" in ts  # the grid glyph character 田
        # Assert
        assert has_glyph, (
            "the grid glyph (田) is the compass-specified icon for the launcher "
            "trigger — a self-contained character, no icon font, no SVG asset. "
            "If it is removed the trigger loses its visual identity and the "
            "component drifts from the compass contract."
        )


class TestShippedBundleCarriesTheContract:
    """The esbuild bundle is what a bundler-less adopter actually executes."""

    def test_bundle_exposes_the_select_event(self):
        # Arrange
        # Act
        in_bundle = _SELECT_EVENT in _bundle_text()
        # Assert
        assert in_bundle, (
            "the select event name is absent from the shipped bundle — an "
            "adopter without a bundler executes this file, so their listener "
            "would never fire. Rebuild per the file's banner."
        )

    def test_bundle_uses_the_same_block(self):
        # Arrange
        # Act
        in_bundle = _CLS in _bundle_text()
        # Assert
        assert in_bundle, (
            "the BEM block name is absent from the shipped bundle — the class "
            "the stylesheet keys on. Rebuild per the file's banner."
        )


class TestStylesheetReachesThePage:
    """0.11.1 shipped badge.css importable by nothing; do not repeat it."""

    @pytest.mark.parametrize("bundle", ["app.css", "all.css"])
    def test_bundle_imports_the_stylesheet(self, bundle):
        # Arrange
        text = (_STATIC / "scitex_sdk/ui/css" / bundle).read_text(encoding="utf-8")
        # Act
        imported = "./app/app-launcher.css" in text
        # Assert
        assert imported, (
            f"{bundle} does not import app/app-launcher.css; adopters would "
            f"get the class names and no styling. Regenerate: "
            f"npx tsx css/_build-index.ts"
        )
