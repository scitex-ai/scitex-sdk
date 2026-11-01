"""Literal filter chrome ownership; filtering data and ordinary search remain leaf-owned."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from ._header_contract import (
    _BLOCK,
    _SKIP,
    _SUFFIXES,
    HeaderFinding,
    _generated_css,
    _source_paths,
)

_SHARED = re.compile(
    r"\.stx-filter-field(?:__[\w-]+|--[\w-]+)?(?![\w-])|\[data-stx-filter-field(?:[=\]\s])"
)
_LOCAL_HINT = re.compile(
    r"\.[\w-]*filter[\w-]*(?:[\s>]+(?:kbd|\.[\w-]*(?:hint|shortcut|kbd)[\w-]*)|(?:__|--|-)(?:hint|shortcut|kbd)[\w-]*)\b",
    re.IGNORECASE,
)


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.findings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = re.sub(
            r"\{%.*?%\}|\{\{.*?\}\}",
            "",
            attrs.get("class") or attrs.get("classname") or "",
        ).split()
        shared = any(c.startswith("stx-filter-field") for c in classes)
        mount = "data-stx-filter-field" in attrs and attrs["data-stx-filter-field"] in {
            None,
            "",
        }
        scope = (
            mount
            or shared
            or bool(
                re.search(
                    r"(?:^|[-_\s])filter(?:$|[-_\s])",
                    " ".join(classes + [attrs.get("id") or ""]),
                )
            )
        )
        if shared or (mount and (tag != "div" or "style" in attrs)):
            self.findings.append(
                (
                    self.getpos()[0],
                    "Filter chrome belongs to the SDK renderer; use an empty data-stx-filter-field mount.",
                )
            )
        if self.stack and any(item[1] for item in self.stack):
            if tag == "kbd" or any(
                re.search(r"(?:hint|shortcut|keyboard)", c, re.IGNORECASE)
                for c in classes
            ):
                self.findings.append(
                    (
                        self.getpos()[0],
                        "Handwritten filter keyboard hints fork the SDK FilterField contract.",
                    )
                )
            if any(item[2] for item in self.stack):
                self.findings.append(
                    (
                        self.getpos()[0],
                        "The data-stx-filter-field mount must be empty; SDK owns its children.",
                    )
                )
        if tag not in {"input", "img", "br", "hr", "meta", "link", "source", "wbr"}:
            self.stack.append((tag, scope, mount))

    def handle_data(self, data):
        if data.strip() and any(item[2] for item in self.stack):
            self.findings.append(
                (self.getpos()[0], "The data-stx-filter-field mount must be empty.")
            )

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def _owner(path, root):
    if (
        path.relative_to(root).as_posix()
        != "src/scitex_sdk/ui/static/scitex_sdk/ui/css/app/filter-field.css"
    ):
        return False
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return False
    project = re.search(
        r"(?ms)^\[project\]\s*$(.*?)(?=^\[|\Z)", manifest.read_text(encoding="utf-8")
    )
    return bool(
        project and re.search(r"(?m)^name\s*=\s*['\"]scitex-sdk['\"]\s*$", project[1])
    )


def scan_filters(root, *, overlays=None, targets=None):
    """Use the header guard's source discovery and Vite ownership boundaries.

    Failed reads/imports propagate to the mandatory dispatcher. Only recognized
    filter chrome is covered; custom result filtering and search inputs are free.
    """
    root = Path(root).resolve()
    overlays = {Path(p).resolve(): text for p, text in (overlays or {}).items()}
    targets = None if targets is None else {Path(p).resolve() for p in targets}
    paths = _source_paths(root) | set(overlays)
    generated = _generated_css(root, paths)
    out = []
    for path in sorted(paths):
        if targets is not None and path not in targets:
            continue
        if not path.is_relative_to(root) or path.suffix.lower() not in _SUFFIXES:
            continue
        if set(path.relative_to(root).parts) & _SKIP or path.resolve() in generated:
            continue
        if not path.is_file() and path not in overlays:
            continue
        text = overlays[path] if path in overlays else path.read_text(encoding="utf-8")
        text = re.sub(
            r"<!--.*?-->|/\*.*?\*/|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
            lambda m: "\n" * m[0].count("\n"),
            text,
            flags=re.DOTALL,
        )
        if path.suffix.lower() != ".css":
            parser = _Markup()
            parser.feed(
                re.sub(
                    r"\{%.*?%\}|\{\{.*?\}\}",
                    lambda m: "\n" * m[0].count("\n"),
                    text,
                    flags=re.S,
                )
            )
            out.extend(
                HeaderFinding(str(path), line, detail)
                for line, detail in parser.findings
            )
            styles = list(
                re.finditer(
                    r"<style\b[^>]*>(.*?)</style\s*>", text, re.IGNORECASE | re.DOTALL
                )
            )
            text = "".join(
                "\n" * text[previous : match.start(1)].count("\n") + match[1]
                for previous, match in zip([0] + [m.end(1) for m in styles], styles)
            )
        if _owner(path, root):
            continue
        for match in _BLOCK.finditer(text):
            selector = re.sub(r":not\([^)]*\)", "", match[1])
            if _SHARED.search(selector) or _LOCAL_HINT.search(selector):
                out.append(
                    HeaderFinding(
                        str(path),
                        text.count("\n", 0, match.start()) + 1,
                        "Shared filter chrome and keyboard hints belong to SDK filter-field.css.",
                    )
                )
    return out
