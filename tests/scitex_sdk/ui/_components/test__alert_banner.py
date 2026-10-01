#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._alert_banner."""

from scitex_sdk.ui._components._alert_banner import AlertBanner


class TestAlertBanner:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(AlertBanner) is AlertBanner

    def test_is_css_only(self):
        # Arrange
        # Act
        # Assert
        assert AlertBanner.ts_entry is None


# EOF
