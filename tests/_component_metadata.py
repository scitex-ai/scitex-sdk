#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The component-metadata sanity check, in one place.

WHY THIS IS NOT IN A conftest ANY MORE, measured 2026-09-17 in this repo:

    pytest tests                                      -> 1701 passed, 0 errors
    pytest tests/scitex_sdk/ui/_components                ->  144 passed, 0 errors
    pytest <64 explicit test-file paths from different directories> \
        -> 24 errors: fixture 'check_metadata' not found

The CI shard runner does NOT pass directories: it builds an explicit weighted list
of test FILE paths and passes those (`pytest-matrix.yml`, the `mapfile -t
TEST_FILES` step). In that shape the subdirectory conftest stops contributing the
fixture to its own tests, at a threshold between 63 and 64 files, with no conftest
import error reported anywhere — while the same file list run as directories, or
in smaller batches, is clean. That is a pytest collection-shape interaction, not a
test defect, and it made every PR in this repo red.

The ROOT conftest is loaded for every test under tests/ regardless of how the
arguments are spelled, so the fixture lives there now. The check itself moved to
this module so that both conftests can reference one implementation without
importing each other (a conftest is not a library, however importable it looks).
"""

from __future__ import annotations

import re

from scitex_sdk.ui._registry import get_component
from tests._checkout import package_dir

PKG_DIR = package_dir()


def check_component_metadata(cls):
    """Verify common metadata fields and on-disk asset existence.

    Either asset may be ``None``: a component can be CSS-only (the nine
    `stx-app-*` styles apps drive with their own handlers) or JS-only
    (monaco-editor, whose styles arrive through its bundle). Requiring both
    is what forced monaco-editor to bypass this helper with a hand-written
    test — so this checks each asset only when declared, and requires at
    least one, which is the property that actually matters: a component
    that ships nothing is a registry entry pointing at nothing.

    Returns the class on success so callers can `assert check_metadata(Cls)`.
    """
    assert cls.name
    # Shape, not value: pinning a literal version here froze every component
    # at 0.1.0 — the first real bump (context-menu 0.2.0) failed this line.
    assert re.fullmatch(r"\d+\.\d+\.\d+", cls.version), (
        f"{cls.name} version {cls.version!r} is not X.Y.Z"
    )
    assert cls.description
    assert cls.ts_entry or cls.css_file, f"{cls.name} declares no asset at all"

    # Registered in registry under its canonical name.
    assert get_component(cls.name) is cls

    if cls.css_file:
        css_path = PKG_DIR / "static" / cls.css_file
        assert css_path.exists(), f"CSS not found: {css_path}"

    if cls.ts_entry:
        ts_path = PKG_DIR / "static" / (cls.ts_entry + ".ts")
        assert ts_path.exists(), f"TS entry not found: {ts_path}"

    # Optional pre-built pure-JS sibling for Django-template consumers
    # (no vite). Verified only when the component declares ``js_file`` —
    # other components stay unchanged.
    js_file = getattr(cls, "js_file", None)
    if js_file:
        js_path = PKG_DIR / "static" / js_file
        assert js_path.exists(), f"JS bundle not found: {js_path}"

    return cls
