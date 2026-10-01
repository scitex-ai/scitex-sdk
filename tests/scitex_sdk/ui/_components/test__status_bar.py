#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__status_bar.py

"""Tests for scitex_sdk.ui._components._status_bar."""

from scitex_sdk.ui._components._status_bar import StatusBar


class TestStatusBar:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(StatusBar) is StatusBar


# EOF
