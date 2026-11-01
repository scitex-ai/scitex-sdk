"""Static ownership checks for SDK app headers and project dropdowns.

Inspect literal source only. Runtime styles and computed inheritance remain
covered by the SDK browser contract suite, not guessed by this scanner.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

_SUFFIXES = {".css", ".html", ".htm", ".tsx", ".jsx"}
_SKIP = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    ".worktrees",
    "tests",
    "examples",
    "docs",
    "_docs",
}
_SHARED = re.compile(
    r"\.stx-app-(?:header|project-selector)(?:__[\w-]+|--[\w-]+)?(?![\w-])|\[data-stx-app-header(?:[=\]\s])"
)
_BLOCK = re.compile(r"([^{}]+)\{([^{}]*)\}")
_PROPERTY = re.compile(
    r"(?:^|;)\s*(?:font[\w-]*|line-height|letter-spacing|padding[\w-]*|border-radius|height|min-height|color|background[\w-]*)\s*:",
    re.IGNORECASE,
)
_OWNER = {"app-header.css", "project-selector.css"}


@dataclass(frozen=True)
class HeaderFinding:
    """An ownership violation at a source location."""

    path: str
    line: int
    detail: str


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.scopes = set()
        self.findings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or attrs.get("classname") or "").split())
        shared = "data-stx-app-header" in attrs or any(
            c.startswith(("stx-app-header", "stx-app-project-selector"))
            for c in classes
        )
        if shared:
            if tag == "header" or any(c.startswith("stx-app-header") for c in classes):
                self.findings.append(
                    (
                        self.getpos()[0],
                        "Handwritten AppHeader markup forks the SDK renderer; use its mount or React binding.",
                    )
                )
            self.scopes.update(c for _, group in self.stack for c in group)
            if "style" in attrs:
                self.findings.append(
                    (
                        self.getpos()[0],
                        "Inline shared-header/dropdown styling forks the SDK contract.",
                    )
                )
        elif tag == "header" and any(
            re.search(r"(?:^|[-_])app[-_]header(?:$|[-_])", c) for c in classes
        ):
            self.findings.append(
                (
                    self.getpos()[0],
                    "Local app-header markup must use the SDK AppHeader contract.",
                )
            )
        if tag not in {"input", "img", "br", "hr", "meta", "link", "source", "wbr"}:
            self.stack.append((tag, classes))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def _owner(path: Path, root: Path) -> bool:
    """Only canonical SDK resources own these selectors, never the whole repo."""
    relative = path.relative_to(root).as_posix()
    if relative not in {
        f"src/scitex_sdk/ui/static/scitex_sdk/ui/css/app/{name}" for name in _OWNER
    }:
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


def _generated_css(root: Path) -> set[Path]:
    """Skip Vite-declared outputs only when authored frontend source is present.

    Bundles include unmodified SDK CSS, so auditing them as consumer overrides
    would reject legitimate imports. The source remains mandatory to inspect.
    """
    generated = set()
    for directory, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _SKIP]
        manifest = Path(directory) / "manifest.json"
        if Path(directory).name != ".vite" or "manifest.json" not in files:
            continue
        base = manifest.parent.parent
        if not any(
            (parent / "frontend/src").is_dir()
            for parent in base.parents
            if parent.is_relative_to(root)
        ):
            continue
        content = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in content.values():
            for relative in [entry.get("file", ""), *entry.get("css", [])]:
                path = (base / relative).resolve()
                if path.suffix == ".css" and path.is_relative_to(base.resolve()):
                    generated.add(path)
    return generated


def scan_headers(
    root: Path | str,
    *,
    overlays: dict[Path, str] | None = None,
    targets: set[Path] | None = None,
) -> list[HeaderFinding]:
    """Scan literal source; read failures propagate so enforcement fails closed.

    Overlays model proposed editor writes. Targets restrict emitted findings,
    while markup context is collected across the repository for scoped CSS.
    Tests/examples/build outputs are excluded from application-source policy.
    """
    root = Path(root).resolve()
    overlays = {Path(p).resolve(): text for p, text in (overlays or {}).items()}
    targets = None if targets is None else {Path(p).resolve() for p in targets}
    if targets is not None and not any(
        path.suffix.lower() in _SUFFIXES for path in targets
    ):
        return []
    generated = _generated_css(root)
    paths = set(overlays)
    for directory, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _SKIP]
        paths.update(Path(directory) / name for name in files)
    sources = {}
    scopes = set()
    out = []
    for path in sorted(paths):
        if path.resolve() in generated:
            continue
        if path.suffix.lower() not in _SUFFIXES or not path.is_relative_to(root):
            continue
        if set(path.relative_to(root).parts) & _SKIP:
            continue
        if not path.is_file() and path not in overlays:
            continue
        text = overlays[path] if path in overlays else path.read_text(encoding="utf-8")
        sources[path] = text
        if path.suffix != ".css":
            parser = _Markup()
            parser.feed(
                re.sub(
                    r"<!--.*?-->|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
                    lambda m: "\n" * m[0].count("\n"),
                    text,
                    flags=re.DOTALL,
                )
            )
            scopes.update(parser.scopes)
            if targets is None or path in targets:
                out.extend(
                    HeaderFinding(str(path), line, detail)
                    for line, detail in parser.findings
                )
    for path, text in sources.items():
        if targets is not None and path not in targets or _owner(path, root):
            continue
        if path.suffix.lower() != ".css":
            # Javascript selector strings are not CSS declarations. Only literal
            # style elements in markup participate in stylesheet ownership.
            styles = list(
                re.finditer(
                    r"<style\b[^>]*>(.*?)</style\s*>", text, re.IGNORECASE | re.DOTALL
                )
            )
            text = "".join(
                "\n" * text[previous : match.start(1)].count("\n") + match[1]
                for previous, match in zip([0] + [m.end(1) for m in styles], styles)
            )
        # Preserve newlines so comments cannot conceal selectors or shift locations.
        text = re.sub(
            r"/\*.*?\*/", lambda m: "\n" * m[0].count("\n"), text, flags=re.DOTALL
        )
        for match in _BLOCK.finditer(text):
            for selector in match[1].split(","):
                positive = re.sub(r":not\([^)]*\)", "", selector)
                direct = bool(_SHARED.search(positive))
                # Hosts may show/hide their own slot content after mounting.
                # This does not grant ownership of SDK buttons or typography.
                own_descendant = re.search(
                    r"\s+(?:\.(?!stx-)[\w-]+|\[data-(?!stx-)[\w-]+\])\s*$", positive
                )
                declarations = [d.strip() for d in match[2].split(";") if d.strip()]
                visibility_only = bool(declarations) and all(
                    re.fullmatch(
                        r"(?:display|visibility)\s*:\s*(?:none|inline|inline-block|block|flex|hidden|visible)",
                        d,
                    )
                    for d in declarations
                )
                if own_descendant and visibility_only:
                    direct = False
                # A single known ancestor followed by a generic button can
                # reach the header. Scoped toolbar descendants are independent.
                generic = re.fullmatch(
                    r"\s*\.([\w-]+)\s+button(?:\s*:[\w()-]+)*\s*", positive
                )
                leak = generic and generic[1] in scopes and _PROPERTY.search(match[2])
                if direct or leak:
                    out.append(
                        HeaderFinding(
                            str(path),
                            text.count("\n", 0, match.start()) + 1,
                            "Shared header/dropdown styles belong to SDK canonical CSS; narrow app styles to content controls.",
                        )
                    )
                    break
    return out
