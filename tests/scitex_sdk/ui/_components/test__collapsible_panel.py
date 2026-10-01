#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._collapsible_panel."""

from scitex_sdk.ui._components._collapsible_panel import CollapsiblePanel


class TestCollapsiblePanel:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(CollapsiblePanel) is CollapsiblePanel

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert CollapsiblePanel.ts_entry is None


# EOF
