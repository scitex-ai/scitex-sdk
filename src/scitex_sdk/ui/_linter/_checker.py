"""File-tree walker that emits UI-101..107 violations.

Walks an input path (directory or single file), classifies each file by
extension into ``css | tsx | html``, and dispatches to a per-extension
regex-driven checker. Each match becomes a :class:`UIViolation`.

Why regex (not a parser)
-----------------------
The rules target high-signal surface patterns (a vanilla ``<select>``
tag, a raw ``#xxxxxx`` literal, a ``::-webkit-scrollbar-thumb { …
background: #… }`` rule) that don't require a real CSS / TSX parser
to detect with reasonable precision. A regex walker keeps the lint
plugin a pure-Python pip dep with zero install footprint — important
since `scitex-ui` is itself a peer of the apps it lints.

Test coverage relies on small no-mocks fixture trees under
``tests/scitex_sdk/ui/_linter/fixtures/`` that exercise each rule's
positive and negative cases.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from ._rules import UIViolation, build_rules


# --------------------------------------------------------------------------- #
# Patterns                                                                    #
# --------------------------------------------------------------------------- #

# UI-101 — vanilla `<select>` opening tag in TSX/HTML that does NOT carry the
# explicit `data-app-themed` opt-in attribute. Multi-line tag bodies allowed.
_SELECT_RE = re.compile(
    r"<select\b(?P<attrs>[^>]*)>",
    re.IGNORECASE,
)
_DATA_APP_THEMED_RE = re.compile(r"data-app-themed\s*=", re.IGNORECASE)

# UI-106 — a <select>…</select> block, so its <option>s can be counted.
_SELECT_BLOCK_RE = re.compile(
    r"<select\b(?P<attrs>[^>]*)>(?P<body>.*?)</select\s*>",
    re.IGNORECASE | re.DOTALL,
)
_OPTION_RE = re.compile(r"<option\b", re.IGNORECASE)

# Option count above which a native <select> stops being scannable. Matches
# Dropdown's DEFAULT_FILTER_THRESHOLD so the lint and the component agree on
# what "long" means; a rule that disagreed with the component it recommends
# would be advice nobody could satisfy.
_LONG_SELECT_OPTIONS = 8

# A <select> already enhanced by, or explicitly opted out of, the Combobox.
# Opt-out is honoured because some long selects are genuinely fine — an
# ordered list the user scrolls by position rather than searches by name.
_COMBOBOX_OPT_OUT_RE = re.compile(
    r"data-(stx-combobox|no-combobox)\s*=", re.IGNORECASE
)

# UI-102 — raw hex / rgb() / rgba() literal anywhere in a CSS file
# (outside an `--scrollbar-*` declaration that itself references var()).
# We treat any literal that's not inside a `var(...)` argument list as raw.
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_RE = re.compile(r"\brgba?\s*\(", re.IGNORECASE)

# Tokens we recognise as `var(--…)` — used to whitelist tokenised values.
_VAR_REF_RE = re.compile(r"var\(\s*--[a-zA-Z0-9_-]+", re.IGNORECASE)

# UI-103 — fingerprint of scitex-sdk ui shell/primitive selectors a consumer
# would likely copy. Keep conservative: focus on a few high-signal
# shell selectors. False-negative tolerance > false-positive tolerance.
_SHELL_FINGERPRINTS = (
    re.compile(r"\.stx-shell-sidebar\b"),
    re.compile(r"\.stx-app-shell\b"),
    re.compile(r"\.scitex-ui-theme\b"),
    re.compile(r"\[data-theme=['\"]dark['\"]]\s*\{"),
    re.compile(r"\.workspace-three-col\b"),
)

# UI-104 — consumer-CSS file path that touches scitex-ui's shell or
# primitives layer. Triggered when a *.css file LIVES UNDER a path
# segment named `scitex_sdk/ui/css/shell/` or `scitex_sdk/ui/css/primitives/`
# AND the walker root is NOT scitex-sdk ui itself. The CLI's
# ``--treat-as-consumer`` flag suppresses this when running inside
# scitex-ui's own dev tree.
_SHELL_PATH_RE = re.compile(r"(?:scitex_ui|scitex_sdk[\\/]+ui)[\\/]+css[\\/]+(shell|primitives)[\\/]+")

# UI-107 — a root-anchored API path LITERAL in client code. Those are the
# ones that break when the app is mounted under a prefix: correct standalone,
# silently wrong embedded.
#
# Deliberately narrow. `/api/` and `/apps/` are the two roots the fleet
# actually uses; a rule matching every leading-slash string would fire on
# hrefs, image paths and CSS urls, and a rule that noisy gets disabled rather
# than obeyed. Measured population when this shipped: 12 literals across 3
# consumer repos, which is what makes `error` an honest severity.
_ABSOLUTE_API_URL_RE = re.compile(r"""["'`](/api/|/apps/u/)""")

# The FIX contains the pattern: apiUrl("/api/items") is the recommended form.
# Without this exemption the rule would flag every correct call site and read
# as "you have 12 violations" to an app that had already fixed all of them.
_API_URL_CALL_RE = re.compile(r"\bapiUrl\s*\(")

# UI-105 — scrollbar rule body containing a raw hex / rgb() literal.
# We use a coarse single-line match: any `::-webkit-scrollbar` selector
# (or `scrollbar-color:` declaration) followed by a raw color literal
# within the same line OR the next 6 lines.
_SCROLLBAR_SELECTOR_RE = re.compile(
    r"(?:::-webkit-scrollbar[a-z-]*|scrollbar-color\s*:)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Walker                                                                      #
# --------------------------------------------------------------------------- #

_EXT_TO_KIND = {
    ".css": "css",
    ".html": "html",
    ".htm": "html",
    ".tsx": "tsx",
    ".jsx": "tsx",
    ".ts": "tsx",
    ".js": "tsx",
}

_DEFAULT_SKIP_DIRS = (
    "node_modules",
    ".venv",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
)


def _iter_files(
    root: Path,
    skip_dirs: Sequence[str] = _DEFAULT_SKIP_DIRS,
) -> Iterator[Path]:
    """Yield every checkable file under ``root``.

    Skips directory names in ``skip_dirs`` to avoid blowing through
    `node_modules/` etc. — a real consumer tree has thousands of those.
    """
    if root.is_file():
        if root.suffix.lower() in _EXT_TO_KIND:
            yield root
        return
    skip = set(skip_dirs)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in skip for part in p.parts):
            continue
        if p.suffix.lower() in _EXT_TO_KIND:
            yield p


def _is_comment_line(line: str) -> bool:
    """Whether ``line`` reads as a comment rather than as code.

    Line-prefix based, which is a real limit and is declared in
    :data:`~scitex_sdk.ui._linter._rules.COVERAGE_GAPS` rather than left for a
    reader to discover. It exists because a grep-shaped rule otherwise matches
    the documentation OF the pattern it forbids: measured 2026-07-30, both of
    scitex-ui's own two matches were comments, and one was the docstring for
    ``apiUrl`` — the very fix UI-107 recommends.

    NOT usable for CSS, which is why ``_hex_or_rgb_positions`` keeps its own
    near-duplicate test instead of calling this. ``#`` starts a comment in the
    JS-ish world and a COLOUR LITERAL in CSS, so treating a ``#``-leading line
    as a comment here would make UI-102 skip every raw hex it exists to find.
    The duplication is deliberate; unifying these two would silently delete a
    rule.
    """
    return not line.strip() or line.lstrip().startswith(("//", "/*", "*", "<!--", "#"))


def _hex_or_rgb_positions(line: str) -> list[int]:
    """Return column positions of raw hex / rgb literals in ``line``.

    We strip out any ``var(--…)`` first so a `color: var(--text)` line
    doesn't accidentally flag a `#3b` inside `--text`'s upstream
    definition. The function operates on a SINGLE line — callers
    feed it one line at a time so violations carry exact line numbers.
    """
    if not line.strip() or line.lstrip().startswith(("//", "/*", "*", "<!--")):
        return []
    stripped = _VAR_REF_RE.sub(" var(...) ", line)
    cols: list[int] = []
    for match in _HEX_RE.finditer(stripped):
        cols.append(match.start())
    for match in _RGB_RE.finditer(stripped):
        cols.append(match.start())
    return cols


def _scan_css(path: Path, lines: Sequence[str], rules) -> Iterator[UIViolation]:
    # UI-103 — shell fingerprint match in a consumer-side CSS file.
    for lineno, line in enumerate(lines, start=1):
        for fp in _SHELL_FINGERPRINTS:
            m = fp.search(line)
            if m:
                yield UIViolation(
                    rule=rules["STX-UI103"],
                    path=str(path),
                    line=lineno,
                    col=m.start(),
                    source_line=line.rstrip("\n"),
                )

    # UI-104 — consumer CSS that *lives under* scitex-ui's shell or
    # primitives tree (i.e. the consumer has a literal copy of the
    # shared foundation layout). Path-based heuristic.
    if _SHELL_PATH_RE.search(str(path)):
        yield UIViolation(
            rule=rules["STX-UI104"],
            path=str(path),
            line=1,
            col=0,
            source_line="",
        )

    # UI-105 — scrollbar declarations that carry raw color literals
    # (no `var(…)` indirection). We look forward up to 6 lines from each
    # scrollbar selector / `scrollbar-color:` declaration.
    for lineno, line in enumerate(lines, start=1):
        if not _SCROLLBAR_SELECTOR_RE.search(line):
            continue
        window = lines[lineno - 1 : min(len(lines), lineno + 6)]
        for offset, w_line in enumerate(window):
            cols = _hex_or_rgb_positions(w_line)
            if cols:
                yield UIViolation(
                    rule=rules["STX-UI105"],
                    path=str(path),
                    line=lineno + offset,
                    col=cols[0],
                    source_line=w_line.rstrip("\n"),
                )
                break

    # UI-102 — any other raw hex / rgb literal in the CSS, but only if
    # the line is NOT already covered by the UI-105 scrollbar pass (we
    # don't want to double-report the same literal under two rule ids).
    scrollbar_lines: set[int] = set()
    for lineno, line in enumerate(lines, start=1):
        if _SCROLLBAR_SELECTOR_RE.search(line):
            for offset in range(7):
                scrollbar_lines.add(lineno + offset)
    for lineno, line in enumerate(lines, start=1):
        if lineno in scrollbar_lines:
            continue
        cols = _hex_or_rgb_positions(line)
        for col in cols:
            yield UIViolation(
                rule=rules["STX-UI102"],
                path=str(path),
                line=lineno,
                col=col,
                source_line=line.rstrip("\n"),
            )


def _scan_tsx_html(path: Path, lines: Sequence[str], rules) -> Iterator[UIViolation]:
    # UI-101 — `<select>` without `data-app-themed`. We join lines so a
    # multi-line opening tag is parsed as a single match; offsets map
    # back via a running line counter.
    joined = "\n".join(lines)
    for match in _SELECT_RE.finditer(joined):
        attrs = match.group("attrs") or ""
        if _DATA_APP_THEMED_RE.search(attrs):
            continue
        # Compute 1-based line/col from match start in joined string.
        pre = joined[: match.start()]
        lineno = pre.count("\n") + 1
        last_nl = pre.rfind("\n")
        col = match.start() - (last_nl + 1)
        yield UIViolation(
            rule=rules["STX-UI101"],
            path=str(path),
            line=lineno,
            col=col,
            source_line=(
                lines[lineno - 1].rstrip("\n") if 1 <= lineno <= len(lines) else ""
            ),
        )

    # UI-106 — a native <select> long enough that scanning it fails. Counted
    # from the literal <option> tags in the markup, so a list populated at
    # runtime by JS is INVISIBLE here. That is a real blind spot and the
    # reason this is a warning rather than an error: absence of a finding is
    # not evidence the picker is short.
    for match in _SELECT_BLOCK_RE.finditer(joined):
        attrs = match.group("attrs") or ""
        if _COMBOBOX_OPT_OUT_RE.search(attrs):
            continue
        if len(_OPTION_RE.findall(match.group("body") or "")) <= _LONG_SELECT_OPTIONS:
            continue
        pre = joined[: match.start()]
        lineno = pre.count("\n") + 1
        last_nl = pre.rfind("\n")
        col = match.start() - (last_nl + 1)
        yield UIViolation(
            rule=rules["STX-UI106"],
            path=str(path),
            line=lineno,
            col=col,
            source_line=(
                lines[lineno - 1].rstrip("\n") if 1 <= lineno <= len(lines) else ""
            ),
        )

    # UI-107 — root-anchored API path literals. Per-LINE, not on the joined
    # text, so the comment and apiUrl() exemptions below are meaningful and
    # each violation carries an exact line number.
    for lineno, line in enumerate(lines, start=1):
        if _is_comment_line(line):
            continue
        # The recommended fix contains the flagged pattern. Skipping the whole
        # line is coarse — a line mixing a correct call and a raw literal is
        # let through — but the opposite error is worse: flagging every correct
        # call site would tell a fully-migrated app it has violations, and a
        # rule that fires on its own remedy is one nobody keeps enabled.
        if _API_URL_CALL_RE.search(line):
            continue
        for match in _ABSOLUTE_API_URL_RE.finditer(line):
            yield UIViolation(
                rule=rules["STX-UI107"],
                path=str(path),
                line=lineno,
                col=match.start(),
                source_line=line.rstrip("\n"),
            )


def scan_path(
    target: Path | str,
    *,
    treat_as_consumer: bool = True,
    skip_dirs: Sequence[str] = _DEFAULT_SKIP_DIRS,
) -> list[UIViolation]:
    """Walk ``target`` and return all UI-101..107 violations found.

    Parameters
    ----------
    target
        Path to a single file or to a directory tree.
    treat_as_consumer
        If True (default), this is a consumer repo lint — UI-104
        (shell/primitives edits) fires when consumer CSS lives under
        the shell/primitives path. Pass False to run inside scitex-ui
        itself, where editing shell/primitives is allowed.
    skip_dirs
        Directory NAMES to skip while walking. Defaults skip
        ``node_modules``, ``.venv``, ``.git`` etc.

    Returns
    -------
    list[UIViolation]
        All violations in walk-order, then by line number within each
        file.
    """
    target_path = Path(target)
    rules = build_rules()
    violations: list[UIViolation] = []
    for path in _iter_files(target_path, skip_dirs=skip_dirs):
        kind = _EXT_TO_KIND.get(path.suffix.lower())
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        if kind == "css":
            for v in _scan_css(path, lines, rules):
                if v.rule.id == "STX-UI104" and not treat_as_consumer:
                    continue
                violations.append(v)
        elif kind in {"tsx", "html"}:
            violations.extend(_scan_tsx_html(path, lines, rules))
    return violations


__all__ = ["scan_path"]
