#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The dropdown filter must be automatic, and there must be only one matcher.

Operator directive 2026-07-28: 「普通にあいまい検索でフィルタはいつも入れてください」
— a long picker always gets a fuzzy filter. An opt-in flag would satisfy the
letter of that and fail it in practice, because some caller always forgets. So
the filter turns itself on above a threshold, and these tests assert that
default rather than the option's existence.

The second concern is sharper: two lists that filter DIFFERENTLY are worse
than one list that does not filter at all, because the user learns the first
one lied. Hence one matcher, shared.
"""

import re

from tests._checkout import package_dir

_STATIC = package_dir() / "static"
_TS = _STATIC / "scitex_sdk/ui/ts"


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def _dropdown_ts() -> str:
    root = _TS / "app/dropdown"
    return _strip_comments("\n".join(p.read_text() for p in root.glob("*.ts")))


def _combobox_ts() -> str:
    root = _TS / "app/combobox"
    return _strip_comments("\n".join(p.read_text() for p in root.glob("*.ts")))


def test_fuzzy_matcher_is_defined_exactly_once():
    # Arrange — a second copy would drift the first time either is "improved",
    # and the drift is invisible until a user notices two pickers disagreeing.
    sources = list(_TS.rglob("*.ts"))

    # Act
    definitions = [
        p.relative_to(_TS).as_posix()
        for p in sources
        if re.search(
            r"^\s*(export )?function fuzzyMatch", _strip_comments(p.read_text()),
            flags=re.MULTILINE,
        )
    ]

    # Assert
    assert definitions == ["_base/fuzzy.ts"], (
        f"fuzzyMatch is defined in {definitions}; it must live only in "
        "_base/fuzzy.ts so every filterable list narrows identically"
    )


def test_combobox_delegates_to_the_shared_matcher():
    # Arrange — Combobox keeps a static fuzzyMatch as public surface, but it
    # must forward rather than reimplement.
    ts = _combobox_ts()

    # Act
    imports_shared = re.search(r'from\s+"\.\./\.\./_base/fuzzy"', ts)

    # Assert
    assert imports_shared, (
        "Combobox no longer imports the shared matcher — it has grown its own "
        "copy, which will drift from Dropdown's"
    )


def test_dropdown_uses_the_shared_matcher():
    # Arrange
    ts = _dropdown_ts()

    # Act
    imports_shared = re.search(r'from\s+"\.\./\.\./_base/fuzzy"', ts)

    # Assert
    assert imports_shared, "Dropdown must filter with the shared matcher"


def test_filter_appears_without_being_asked_for():
    # Arrange — the whole directive. If `filter` is unset the component must
    # decide from the item count, not default to off.
    ts = _dropdown_ts()

    # Act
    auto = re.search(r"filterThreshold\s*\?\?\s*DEFAULT_FILTER_THRESHOLD", ts)

    # Assert
    assert auto, (
        "no automatic threshold: the filter only appears when a caller opts "
        "in, and the callers who most need it are the ones who will not"
    )


def test_threshold_default_is_declared_as_a_constant():
    # Arrange — a magic number inline is untunable and undocumented.
    ts = _dropdown_ts()

    # Act
    declared = re.search(r"DEFAULT_FILTER_THRESHOLD\s*=\s*(\d+)", ts)

    # Assert
    assert declared, "the auto-filter threshold must be a named constant"


def test_query_resets_when_the_menu_reopens():
    # Arrange — a dropdown that reopens still filtered looks like it lost its
    # items, and the user has no idea why.
    ts = _dropdown_ts()

    # Act
    resets = re.search(r"this\.query\s*=\s*\"\"", ts)

    # Assert
    assert resets, "reopening must clear the previous query"


def test_no_matches_renders_an_empty_state():
    # Arrange — an empty menu is indistinguishable from a broken one.
    ts = _dropdown_ts()
    css = _strip_comments(
        (_STATIC / "scitex_sdk/ui/css/app/dropdown.css").read_text()
    )

    # Act
    in_module = re.search(r"__empty", ts)
    in_css = re.search(r"\.stx-app-dropdown__empty", css)

    # Assert
    assert in_module and in_css, (
        "an empty result must say so, and must be styled — an unstyled empty "
        "state reads as a rendering failure"
    )


def test_trigger_listener_is_removable():
    # Arrange — the original passed an anonymous function to addEventListener,
    # so destroy() could not remove it: every destroyed Dropdown left a live
    # listener and a re-created one fired toggle() twice per click.
    ts = _dropdown_ts()

    # Act
    removes = re.search(
        r"removeEventListener\(\s*\"click\",\s*this\.triggerClickHandler", ts
    )

    # Assert
    assert removes, "destroy() must remove the trigger listener it added"
