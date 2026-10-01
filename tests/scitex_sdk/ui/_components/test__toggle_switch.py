#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._toggle_switch."""

from scitex_sdk.ui._components._toggle_switch import ToggleSwitch


class TestToggleSwitch:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(ToggleSwitch) is ToggleSwitch

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert ToggleSwitch.ts_entry is None


# EOF
