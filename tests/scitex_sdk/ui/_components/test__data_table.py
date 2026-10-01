#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__data_table.py

"""Tests for scitex_sdk.ui._components._data_table."""

from scitex_sdk.ui._components._data_table import DataTable


class TestDataTable:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(DataTable) is DataTable


# EOF
