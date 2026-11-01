"""Ownership of shared viewport frames and the absence of app-top accent stripes."""

from __future__ import annotations

import re
from pathlib import Path

from ._header_contract import (
    _BLOCK,
    _SKIP,
    _SUFFIXES,
    HeaderFinding,
    _generated_css,
    _source_paths,
)

_FRAME = r"(?:\.(?:workspace-three-col|workspace-layout|workspace-content)|#(?:workspace-layout|workspace-three-col))"
_ROOT = rf"(?:{_FRAME}|#(?:main-content|root|app-root)|\.(?:stx-shell-content|stx-app-root|app-root)|\[data-app-accent(?:[^\]]*)\])"
_SUFFIX = r"(?:\[[^\]]+\]|\.[\w-]+|:(?!:)[\w()-]+)*"
_FRAME_SELECTOR = re.compile(rf"(?:^|[\s>+~]){_FRAME}{_SUFFIX}\s*$")
_STRIPE_SELECTOR = re.compile(rf"(?:^|[\s>+~]){_ROOT}{_SUFFIX}::(?:before|after)\s*$")
_FRAME_PROPERTIES = re.compile(
    r"^(?:width|min-width|max-width|margin(?:-[\w-]+)?|background(?:-[\w-]+)?)$"
)
_OWNERS = {
    "scitex-sdk": {
        "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/app-shell.css",
        "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/workspace-three-col.css",
        "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/mobile.css",
        "src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell/stx-shell-sidebar.css",
    },
    "scitex-hub": {
        "static/shared/css/components/workspace-layout.css",
        "static/shared/css/components/workspace-chat-embed.css",
    }
    | {
        f"static/shared/css/layouts/{name}.css"
        for name in (
            "site-content-frame",
            "leaf-host-chrome",
            "global-base",
            "platform-backdrop",
        )
    },
}


def _owner(path, root):
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return False
    project = re.search(
        r"(?ms)^\[project\]\s*$(.*?)(?=^\[|\Z)", manifest.read_text(encoding="utf-8")
    )
    name = (
        re.search(r"(?m)^name\s*=\s*['\"]([^'\"]+)['\"]\s*$", project[1])
        if project
        else None
    )
    return bool(
        name and path.relative_to(root).as_posix() in _OWNERS.get(name[1], set())
    )


def _visible_stripe(declarations):
    """Recognize a thin painted top pseudo-element, never a general bubble."""
    if (
        declarations.get("display") == "none"
        or declarations.get("visibility") == "hidden"
    ):
        return False
    if declarations.get("content") in {"none", "normal"}:
        return False
    top = declarations.get("top", declarations.get("inset-block-start", ""))
    height = declarations.get("height", declarations.get("block-size", ""))
    thin = re.fullmatch(r"(?:[1-4](?:\.0+)?px|0?\.[1-4](?:0*)rem)", height)
    paint = declarations.get(
        "background",
        declarations.get("background-color", declarations.get("background-image", "")),
    )
    painted = bool(
        paint and paint not in {"none", "transparent", "inherit", "initial", "unset"}
    )
    border = declarations.get("border-top", declarations.get("border-block-start", ""))
    zero = {"0", "0px", "0rem"}
    spanning = (
        declarations.get("left") in zero
        and declarations.get("right") in zero
        or declarations.get("inset-inline") in zero
        or declarations.get("width") in {"100%", "100vw"}
        or declarations.get("display") == "block"
    )
    return (
        top in zero
        and spanning
        and bool(
            (thin and painted)
            or (border and not re.match(r"(?:0(?:px)?\b|none\b)", border))
        )
    )


def scan_shell(root, *, overlays=None, targets=None):
    """Inspect literal shared-wrapper CSS through common source discovery."""
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
            r"/\*.*?\*/|<!--.*?-->|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
            lambda m: "\n" * m[0].count("\n"),
            text,
            flags=re.DOTALL,
        )
        if path.suffix.lower() != ".css":
            styles = list(
                re.finditer(
                    r"<style\b[^>]*>(.*?)</style\s*>", text, re.IGNORECASE | re.DOTALL
                )
            )
            text = "".join(
                "\n" * text[previous : match.start(1)].count("\n") + match[1]
                for previous, match in zip([0] + [m.end(1) for m in styles], styles)
            )
        for match in _BLOCK.finditer(text):
            declarations = {}
            for declaration in match[2].split(";"):
                name, separator, value = declaration.partition(":")
                if separator:
                    declarations[name.strip().lower()] = re.sub(
                        r"\s*!important\s*$", "", value.strip(), flags=re.IGNORECASE
                    ).lower()
            for selector in match[1].split(","):
                selector = re.sub(r":not\([^)]*\)", "", selector).strip()
                stripe = _STRIPE_SELECTOR.search(selector) and _visible_stripe(
                    declarations
                )
                frame = (
                    _FRAME_SELECTOR.search(selector)
                    and any(_FRAME_PROPERTIES.match(name) for name in declarations)
                    and not _owner(path, root)
                )
                if stripe or frame:
                    detail = (
                        "Do not add a horizontal accent stripe above app content."
                        if stripe
                        else "Shared viewport width, margins, and background belong to the host frame stylesheet."
                    )
                    out.append(
                        HeaderFinding(
                            str(path), text.count("\n", 0, match.start()) + 1, detail
                        )
                    )
                    break
    return out
