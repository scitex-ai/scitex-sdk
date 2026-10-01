#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__resizer.py

"""Tests for scitex_sdk.ui._components._resizer."""

from scitex_sdk.ui._components._resizer import Resizer


class TestResizer:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Resizer) is Resizer


# EOF
