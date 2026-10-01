#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._badge."""

from scitex_sdk.ui._components._badge import Badge


class TestBadge:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Badge) is Badge

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert Badge.ts_entry is None


# EOF
