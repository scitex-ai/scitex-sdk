#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._import_export (the compass L623 pattern).

The Python half is a registry metadata object, so ``check_metadata`` covers its
shape (the same convention as every other ``test__*.py`` here). The behaviour
half lives in the TypeScript module and its esbuild bundle, and this repo has no
JS test runner — so, like ``test__context_menu.py``, it is verified statically:
recompute the emitted BEM classes and the event contract from source and compare
them against the stylesheet and the shipped bundle. The point is the CROSS-
language agreement (what the module writes is styled, and what the event is
named), which no single-language check can see.
"""

import re

from scitex_sdk import ui as scitex_ui  # noqa: F401  (import registers every component)
from tests._checkout import package_dir
from tests.develop.test_rendered_classes_have_styles import _covered
from scitex_sdk.ui._components._import_export import ImportExport

_STATIC = package_dir() / "static"

# The wire literal, not a guess: the constant the module exports and the app
# listens on. If it changes, both this test and every consumer break together.
_CLS = "stx-app-import-export"
_CONFIRM_EVENT = "stx-import-export:confirm"


def _ts_text() -> str:
    root = _STATIC / "scitex_sdk/ui/ts/app/import-export"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.glob("*.ts")))


def _css_text() -> str:
    return (_STATIC / ImportExport.css_file).read_text(encoding="utf-8")


def _bundle_text() -> str:
    return (_STATIC / ImportExport.js_file).read_text(encoding="utf-8")


def _emitted_classes() -> set[str]:
    """Every BEM class the module writes.

    Multi-class template literals are the trap here: ```${CLS}__trigger
    stx-button``` and ```${CLS}__confirm stx-button stx-button--primary```
    each carry a standard button class after the BEM suffix. The shared
    class-manifest grammar stops at the first non-name token, so it records
    neither ``__trigger`` nor ``__confirm`` (the manifest is a declared
    LOWER_BOUND, so that is in-contract — this test documents the fuller set
    rather than patching a shared guard). Tokenising on whitespace and keeping
    only the ``__``/``--`` tokens recovers the true emitted population.
    """
    emitted = {_CLS}
    for group in re.findall(r"\$\{CLS\}([^`]*)", _ts_text()):
        for tok in group.split():
            if tok.startswith("__") or tok.startswith("--"):
                emitted.add(_CLS + tok)
    return emitted


class TestImportExport:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ImportExport) is ImportExport

    def test_ships_behaviour_not_only_styling(self):
        # Arrange
        # Act
        entry = ImportExport.ts_entry
        # Assert
        assert entry == "scitex_sdk/ui/ts/app/import-export/index", (
            "the TS entry declares the pattern's mechanics (trigger, format "
            "list, confirm/cancel flow); without it list_components() reveals "
            "styling with no behaviour and every adopter re-implements it"
        )

    def test_confirm_event_is_an_exported_constant(self):
        # Arrange
        ts = _ts_text()
        # Act
        exported = f'export const IMPORT_EXPORT_CONFIRM = "{_CONFIRM_EVENT}"' in ts
        # Assert
        assert exported, (
            "the confirm event name is the wire contract apps listen on; it "
            "must be an exported constant, not a string buried in a handler "
            "that can drift from its import site"
        )


class TestMarkupMatchesStylesheet:
    """The module builds DOM by hand, so a CSS rename would silently orphan it.

    Recomputed from both files (not asserted by memory): a class the module
    emits but no stylesheet rule reaches would render unstyled, and the drift
    guard's block-level coverage convention (an element is covered when its
    block is styled — e.g. ``__body``) is reused from _covered rather than
    re-decided here.
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
            f"the ${{CLS}} template literals, so this guard would pass no "
            f"matter what the module emitted"
        )

    def test_trigger_confirm_and_cancel_use_the_standard_button(self):
        # Arrange
        # Act
        ts = _ts_text()
        offenders = [
            part
            for part in ("__trigger", "__confirm", "__cancel")
            if not re.search(rf"\${{CLS}}{re.escape(part)}[^`]*stx-button", ts)
        ]
        # Assert
        assert not offenders, (
            f"{offenders} must carry the standard stx-button class — the "
            f"confirm/cancel bar is a consumer of the form-controls standard, "
            f"not a re-definition of buttons, so it cannot drift from every "
            f"other control"
        )


class TestShippedBundleCarriesTheContract:
    """The esbuild bundle is what a bundler-less adopter actually executes.

    A source-only contract would pass every other check while the shipped
    ``.js`` (the path a Django template hits with no vite) is stale. Pin the
    two literals the app depends on in the bundle itself.
    """

    def test_bundle_exposes_the_confirm_event(self):
        # Arrange
        # Act
        in_bundle = _CONFIRM_EVENT in _bundle_text()
        # Assert
        assert in_bundle, (
            "the confirm event name is absent from the shipped bundle — an "
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


# EOF
