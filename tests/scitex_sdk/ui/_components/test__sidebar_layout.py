#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._sidebar_layout."""

from scitex_sdk.ui._components._sidebar_layout import SidebarLayout


class TestSidebarLayout:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(SidebarLayout) is SidebarLayout

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert SidebarLayout.ts_entry is None


# EOF
