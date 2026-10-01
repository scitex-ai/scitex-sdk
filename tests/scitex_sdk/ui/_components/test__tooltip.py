#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__tooltip.py

"""Tests for scitex_sdk.ui._components._tooltip."""

from scitex_sdk.ui._components._tooltip import Tooltip


class TestTooltip:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Tooltip) is Tooltip


# EOF
