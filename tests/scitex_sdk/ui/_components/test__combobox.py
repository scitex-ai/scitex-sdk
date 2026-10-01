#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__combobox.py

"""Tests for scitex_sdk.ui._components._combobox."""

from scitex_sdk.ui._components._combobox import Combobox


class TestCombobox:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Combobox) is Combobox


# EOF
