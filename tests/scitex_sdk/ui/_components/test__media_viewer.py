#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__media_viewer.py

"""Tests for scitex_sdk.ui._components._media_viewer."""

from scitex_sdk.ui._components._media_viewer import MediaViewer


class TestMediaViewer:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(MediaViewer) is MediaViewer


# EOF
