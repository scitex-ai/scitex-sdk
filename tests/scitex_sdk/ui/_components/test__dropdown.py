#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__dropdown.py

"""Tests for scitex_sdk.ui._components._dropdown."""

from scitex_sdk.ui._components._dropdown import Dropdown


class TestDropdown:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Dropdown) is Dropdown


# EOF
