#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._context_menu."""

import re

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._context_menu import ContextMenu

_STATIC = package_dir() / "static"


class TestContextMenu:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ContextMenu) is ContextMenu

    def test_ships_behaviour_not_only_styling(self):
        # Arrange
        # Act
        entry = ContextMenu.ts_entry
        # Assert
        assert entry == "scitex_sdk/ui/ts/app/context-menu/index", (
            "context-menu shipped styling with no mechanics until 0.3.0, which is "
            "why every adopter re-implemented positioning and dismissal; the TS "
            "entry must stay declared or list_components() hides it again"
        )

    def test_declared_ts_entry_ships(self):
        # Arrange
        # ts_entry omits the extension by package convention; conftest appends it.
        entry = _STATIC / f"{ContextMenu.ts_entry}.ts"
        # Act
        exists = entry.is_file()
        # Assert
        assert exists, f"{ContextMenu.ts_entry} is declared but not in the package"


class TestMarkupMatchesStylesheet:
    """The module builds DOM by hand, so a CSS rename would silently orphan it.

    Nothing at runtime connects the emitted class strings to the stylesheet that
    styles them: rename a block in the CSS and the menu keeps rendering, unstyled.
    This recomputes both sides from the files and compares.
    """

    def _css(self) -> str:
        return (_STATIC / ContextMenu.css_file).read_text()

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/context-menu"
        return "\n".join(p.read_text() for p in root.glob("*.ts"))

    def test_every_class_the_module_emits_is_styled(self):
        # Arrange
        emitted = set(re.findall(r'"(stx-app-context-menu[a-z_-]*)"', self._ts()))
        css = self._css()
        # Act
        unstyled = sorted(c for c in emitted if f".{c}" not in css)
        # Assert
        assert not unstyled, (
            f"the module emits {unstyled}, which the stylesheet does not define; "
            f"the menu would render unstyled"
        )

    def test_guard_is_not_vacuous(self):
        # Arrange
        # Act
        emitted = set(re.findall(r'"(stx-app-context-menu[a-z_-]*)"', self._ts()))
        # Assert
        assert len(emitted) >= 4, (
            f"only found {emitted}; the extraction regex stopped matching, so this "
            f"guard would pass no matter what the module emitted"
        )

    def test_z_index_is_tokenised(self):
        # Arrange
        css = self._css()
        # Act
        tokenised = "var(--stx-context-menu-z" in css
        # Assert
        assert tokenised, (
            "z-index must stay a token: figrecipe collides with the default 1000 "
            "and scitex-cards does not, so adopters set the token rather than "
            "overriding the selector"
        )


# EOF
