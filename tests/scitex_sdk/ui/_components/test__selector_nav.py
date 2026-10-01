#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._selector_nav."""

from scitex_sdk.ui._components._selector_nav import SelectorNav


class TestSelectorNav:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(SelectorNav) is SelectorNav

    def test_ships_a_ts_entry(self):
        # Arrange
        component = SelectorNav
        # Act
        entry = component.ts_entry
        # Assert
        assert entry == "scitex_sdk/ui/ts/app/selector-nav/index"

    def test_ships_a_prebuilt_module_for_pages_without_a_bundler(self):
        # Arrange
        component = SelectorNav
        # Act
        module = component.js_file
        # Assert
        assert module == "scitex_sdk/ui/js/app/selector-nav.js"

    def test_description_names_both_presentations(self):
        # Arrange — the description is what a consumer reads to know whether
        # this is the primitive they want; ONE shape would undersell it.
        component = SelectorNav
        # Act
        description = component.description.lower()
        # Assert
        assert "tab strip" in description and "cascading" in description
