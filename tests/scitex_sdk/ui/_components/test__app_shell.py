#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/test__app_shell.py

"""Tests for scitex_sdk.ui._components._app_shell."""

from scitex_sdk.ui._components._app_shell import AppShell


class TestAppShell:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(AppShell) is AppShell


# EOF
