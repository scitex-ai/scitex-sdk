#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._package_docs_sidebar."""

from scitex_sdk.ui._components._package_docs_sidebar import PackageDocsSidebar


class TestPackageDocsSidebar:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        result = check_metadata(PackageDocsSidebar)
        # Assert
        assert result is PackageDocsSidebar

    def test_api_endpoint_is_set(self):
        # Arrange
        # Act
        endpoint = PackageDocsSidebar.api_endpoint
        # Assert
        assert endpoint


# EOF
