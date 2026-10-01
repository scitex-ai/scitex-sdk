#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._miller_columns."""

from scitex_sdk.ui._components._miller_columns import MillerColumns


class TestMillerColumns:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(MillerColumns) is MillerColumns

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert MillerColumns.ts_entry is None


# EOF
