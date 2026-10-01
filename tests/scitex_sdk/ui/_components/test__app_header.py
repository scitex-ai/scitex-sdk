#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._app_header."""

from scitex_sdk.ui._components._app_header import AppHeader


class TestAppHeader:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(AppHeader) is AppHeader

    def test_description_names_the_header(self):
        # Arrange
        component = AppHeader
        # Act
        description = component.description.lower()
        # Assert
        assert "header" in description

    def test_ships_a_ts_entry(self):
        # Arrange
        component = AppHeader
        # Act
        entry = component.ts_entry
        # Assert
        assert entry == "scitex_sdk/ui/ts/app/app-header/index"

    def test_ships_a_stylesheet(self):
        # Arrange
        component = AppHeader
        # Act
        stylesheet = component.css_file
        # Assert
        assert stylesheet == "scitex_sdk/ui/css/app/app-header.css"

    def test_ships_a_prebuilt_module_for_pages_without_a_bundler(self):
        # Arrange
        component = AppHeader
        # Act
        module = component.js_file
        # Assert
        assert module == "scitex_sdk/ui/js/app/app-header.js"
