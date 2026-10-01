#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._recent_pane."""

from scitex_sdk.ui._components._recent_pane import RecentPane


class TestRecentPane:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(RecentPane) is RecentPane

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert RecentPane.ts_entry is None


# EOF
