#!/usr/bin/env python3
"""Launcher-overlay CSS contract: no page-level reserved band.

The overlay's header comment (hub PR 923 S4) forbids reserving a band on the
page: the app surface is the whole viewport and the dock collision is a
runtime job (ts/shell/launcher-overlay.ts). This test makes that refusal a
gate rather than prose: it fails if launcher-overlay.css ever gains a rule
that sets a padding/margin declaration on a page-level selector
(body/html/:root).
"""

from __future__ import annotations

import re
from pathlib import Path

CSS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/launcher-overlay.css"
)

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE_RE = re.compile(r"([^{}@]+)\{([^{}]*)\}")
_PAGE_SELECTOR_RE = re.compile(r"(?:^|[\s,>+~])(?:body|html|:root)(?:$|[\s,.:#>~\[])")


def _page_padding_rules(css: str) -> list[str]:
    hits = []
    for match in _RULE_RE.finditer(css):
        selector, declarations = match.group(1), match.group(2)
        if not _PAGE_SELECTOR_RE.search(selector):
            continue
        for declaration in declarations.split(";"):
            name = declaration.split(":", 1)[0].strip().lower()
            if name in {"padding", "margin"} or name.startswith(("padding-", "margin-")):
                hits.append(f"{selector.strip()} -> {name}")
    return hits


def test_launcher_overlay_css_has_no_page_reserve() -> None:
    # Arrange
    path = CSS_PATH
    # Act
    exists = path.is_file()
    css = _COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
    result = (exists, bool(css.strip()), _page_padding_rules(css))
    # Assert
    assert result == (True, True, [])
