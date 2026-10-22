#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The declarative leaf-app launcher-group contract (operator 2026-10-23).

A leaf app declares, in its manifest, which launcher-page section its tile
belongs to: foundation / work / publication. Omitted ``group`` is undeclared
(``None``) — the host keeps its existing grouping as the fallback, so adoption
is per-leaf. A typo'd group fails loud at validation, never mis-groups a tile.

One assertion per test (STX-TQ007); AAA markers on their own lines (STX-TQ002).
No mocks (PA-306).
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import django
import pytest
from django.conf import settings

if not settings.configured:
    # Identical in every scitex-app django test module: Django configures
    # settings once per process and the module order is not ours to choose,
    # so the blocks must agree or the fixture depends on luck.
    settings.configure(
        DEFAULT_CHARSET="utf-8",
        ALLOWED_HOSTS=["*"],
        DATABASES={},
        INSTALLED_APPS=["django.contrib.contenttypes"],
    )
    django.setup()

from scitex_sdk.app._django import ScitexAppConfig  # noqa: E402
from scitex_sdk.app.appmaker._validate._manifest import (  # noqa: E402
    GROUP_FOUNDATION,
    GROUP_PUBLICATION,
    GROUP_WORK,
    VALID_GROUPS,
    normalize_group,
)


class TestNormalizeGroup:
    def test_none_is_undeclared(self):
        # Arrange
        value = None
        # Act
        got = normalize_group(value)
        # Assert
        assert got is None

    def test_empty_is_undeclared(self):
        # Arrange
        value = "   "
        # Act
        got = normalize_group(value)
        # Assert
        assert got is None

    def test_mixed_case_normalizes_to_lower(self):
        # Arrange — same convention as scope: canonical lowercase, any case in.
        value = "Work"
        # Act
        got = normalize_group(value)
        # Assert
        assert got == GROUP_WORK

    def test_typo_raises(self):
        # Arrange
        value = "foundatoin"
        # Act
        with pytest.raises(ValueError, match="'group'"):
            # Assert — raised, not guessed.
            normalize_group(value)

    def test_valid_groups_are_the_three_sections(self):
        # Arrange
        expected = ("foundation", "work", "publication")
        # Act
        got = VALID_GROUPS
        # Assert
        assert got == expected


def _make_app_config(tmp_path: Path, group_value) -> ScitexAppConfig:
    mod = types.ModuleType("myapp._django")
    mod.__file__ = str(tmp_path / "__init__.py")
    cfg = ScitexAppConfig("myapp._django", mod)
    manifest = {
        "name": "myapp",
        "slug": "myapp",
        "label": "My App",
        "pip_package": "my-app",
        "icon": "fas fa-puzzle-piece",
        "license": "MIT",
    }
    if group_value is not None:
        manifest["group"] = group_value
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return cfg


class TestAppConfigGroupAccessor:
    def test_omitted_group_is_undeclared(self, tmp_path):
        # Arrange
        cfg = _make_app_config(tmp_path, None)
        # Act
        got = cfg.app_group
        # Assert
        assert got is None

    def test_declared_group_is_normalized(self, tmp_path):
        # Arrange
        cfg = _make_app_config(tmp_path, "Foundation")
        # Act
        got = cfg.app_group
        # Assert
        assert got == GROUP_FOUNDATION

    def test_publication_group_reads_through(self, tmp_path):
        # Arrange
        cfg = _make_app_config(tmp_path, "publication")
        # Act
        got = cfg.app_group
        # Assert
        assert got == GROUP_PUBLICATION
