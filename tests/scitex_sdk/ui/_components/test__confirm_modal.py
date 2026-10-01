#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__confirm_modal.py

"""Tests for scitex_sdk.ui._components._confirm_modal."""

from scitex_sdk.ui._components._confirm_modal import ConfirmModal


class TestConfirmModal:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ConfirmModal) is ConfirmModal


# EOF
