#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._settings_card."""

from scitex_sdk.ui._components._settings_card import SettingsCard


class TestSettingsCard:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(SettingsCard) is SettingsCard

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert SettingsCard.ts_entry is None


# EOF
