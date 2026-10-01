#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__theme_provider.py

"""Tests for scitex_sdk.ui._components._theme_provider."""

from scitex_sdk.ui._components._theme_provider import ThemeProvider


class TestThemeProvider:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ThemeProvider) is ThemeProvider


# EOF
