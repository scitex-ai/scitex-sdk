"""Half-pair drift guard, PRODUCER direction.

A class WRITTEN by this package's code (ts/ or react/) must be STYLED by
this package's css/ — unless it sits on the reasoned ceiling below.

Mirror of tests/develop/test_shell_layout_classes_have_writers.py (consumer
direction: a styled class must have a writer). The two directions fail
differently:

    consumer with no producer   a rule that can never match — nearly always
                                a bug (shipped first, commit 23c1c30)
    producer with no consumer   markup carrying a class no stylesheet
                                touches — sometimes intentional (inline
                                styling, structural hooks), sometimes a
                                feature that silently renders unstyled

The consumer guard's ceiling ratchet is adopted here, and so is the lesson
from its first draft: a denominator guard must assert a FLOOR, not mere
non-emptiness.

EXTRACTOR IS CONTEXT-AWARE BY CONSTRUCTION. The 2026-09-10 calibration
sweep matched 57 namespaced strings in ts/ + react/; 26 of them were NOT
class writes: 12 element IDs (getElementById, the SIDEBAR_IDS array), 9
localStorage keys, the stx-mount META name, a CustomEvent name, a CSS
custom property (--stx-verdict-*) and a config storageKey default. A
string-keyed detector reading those as classes would have shipped an
amnesty list of infrastructure names. Only class-ASSIGNMENT syntax counts:

    className = "x" | 'x' | `x` | `prefix${...}`
    classList.add / remove / toggle("x")
    class="x" inside HTML template strings
    const CLS = "base"  +  `${CLS}...`   (grammar imported from
                                          test_class_manifest_matches_source —
                                          the shipped consumer of the same
                                          convention; one source for it)

A dynamic class `base--${kind}` enters as the FAMILY ``base--``; it is
covered when any styled selector extends that base (open modifier set, the
same convention the manifest declares).

Card: scitex-ui-two-parametrized-guards-collect-an-empty-set-20260905,
DoD 3/5 (producer direction), design recorded 2026-09-09.
"""

from __future__ import annotations

import re

from tests._checkout import package_dir
from tests.develop.test_class_manifest_matches_source import _BUILT, _CLS

_STATIC = package_dir() / "static" / "scitex_sdk" / "ui"

#: Namespace roots this package owns. The WRITTEN side is scoped to these;
#: the styled side is NOT — a written class may be styled by any selector,
#: and a wider styled set only removes false candidates (the safe direction).
_NS = r"(?:stx|workspace|ws|brand|wft)"
_CLS_NAME = r"[A-Za-z][\w-]*"
#: A namespaced BEM class: root, then one or more hyphen-joined segments.
#: The first draft used root + single letter, which rejected every hyphenated
#: name — stx-pdf-page, the dominant shape — and let only CLS-built bases
#: through; the first run missed 18 writes while BOTH positive controls
#: passed via the CLS path (controls aimed at the component that worked).
#: Measured and corrected 2026-09-10.
_NS_NAME = _NS + r"(?:-[\w-]+)+"

# className = "literal(s)" — quoted form
_RE_CLASSNAME_Q = re.compile(r"\.?className\s*=\s*[\"']([^\"'\n]+)[\"']")
# className = `template` — may carry ${...}
_RE_CLASSNAME_T = re.compile(r"\.?className\s*=\s*`([^`\n]*)`")
# classList.add / remove / toggle( args ) — args scanned for quoted names
_RE_CLASSLIST = re.compile(r"\.classList\.(?:add|remove|toggle)\(([^)\n]+)\)")
# class="..." inside HTML template strings
_RE_HTML_CLASS = re.compile(r"\bclass\s*=\s*[\"']([^\"'\n>]+)[\"']")
# quoted namespaced tokens, for the classList argument scan
_RE_QUOTED_NS = re.compile(r"[\"'](" + _NS_NAME + r")[\"']")
# a family: namespaced prefix ending right before ${  (base--${kind})
_RE_FAMILY = re.compile(r"(" + _NS_NAME + r"--?)\$\{")


def _ts_files():
    return sorted(list(_STATIC.glob("ts/**/*.ts")) + list(_STATIC.glob("react/**/*.tsx")))


def _css_files():
    return sorted(_STATIC.glob("css/**/*.css"))


def _written_classes() -> dict[str, set[str]]:
    """class (or family) -> set of file:line where it is WRITTEN."""
    found: dict[str, set[str]] = {}

    def add(name: str, loc: str) -> None:
        found.setdefault(name, set()).add(loc)

    for p in _ts_files():
        rel = p.relative_to(_STATIC).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")

        # the CLS convention: base const + `${CLS}...` builds (shared grammar)
        base = _CLS.search(text)
        if base:
            b = base.group(1)
            for i, line in enumerate(text.splitlines(), 1):
                if "const CLS" in line:
                    add(b, f"{rel}:{i}")
            for m in _BUILT.finditer(text):
                elem = re.match(r"(__[\w-]+)", m.group(1))
                if elem:
                    add(b + elem.group(1), rel + " (CLS-built)")

        for i, line in enumerate(text.splitlines(), 1):
            for m in _RE_CLASSNAME_Q.finditer(line):
                for name in m.group(1).split():
                    if re.fullmatch(_NS_NAME, name):
                        add(name, f"{rel}:{i}")
            for m in _RE_CLASSNAME_T.finditer(line):
                body = m.group(1)
                fm = _RE_FAMILY.search(body)
                if fm:
                    add(fm.group(1), f"{rel}:{i}")
                elif "${" not in body:
                    name = body.strip()
                    if re.fullmatch(_NS_NAME, name):
                        add(name, f"{rel}:{i}")
            for m in _RE_CLASSLIST.finditer(line):
                for g in _RE_QUOTED_NS.findall(m.group(1)):
                    add(g, f"{rel}:{i}")
                if "`" in m.group(1):
                    fm = _RE_FAMILY.search(m.group(1))
                    if fm:
                        add(fm.group(1), f"{rel}:{i}")
            for m in _RE_HTML_CLASS.finditer(line):
                for name in m.group(1).split():
                    if re.fullmatch(_NS_NAME, name):
                        add(name, f"{rel}:{i}")
    return found


def _styled_classes() -> set[str]:
    out: set[str] = set()
    for p in _css_files():
        out.update(re.findall(r"\.([\w][\w-]*)", p.read_text(encoding="utf-8", errors="replace")))
    return out


def _covered(name: str, styled: set[str]) -> bool:
    """A written class (or family) is covered when a selector names it,
    names its block, or extends it as element/modifier."""
    if name in styled:
        return True
    if name.endswith("--"):  # open modifier family
        stem = name[:-2]
        return any(
            s == stem or s.startswith(stem + "--") or s.startswith(stem + "__")
            for s in styled
        )
    # Symmetric on purpose: a written BLOCK is covered when its ELEMENTS are
    # styled (`.x__el` implies the `.x` container exists), and a written
    # ELEMENT is covered when its BLOCK is styled. Dropping either direction
    # flags every bare container block as an orphan.
    return any(
        name.startswith(s + "--") or name.startswith(s + "__")
        or s.startswith(name + "--") or s.startswith(name + "__")
        for s in styled
    )


# ── Reasoned ceiling ────────────────────────────────────────────────────────
# Two populations, both measured 2026-09-10 (see the card comments).

_DEAD_TREE = (
    "dead ts/ fork side — unreachable from every entry point (30-file "
    "subtree, measured 2026-09-06); disposition on "
    "scitex-ui-app-file-browser-is-a-six-file-fork-of-shell-workspace-files-"
    "tree-20260903"
)


def _inline_hook(f: str, note: str) -> str:
    return f"structural hook — styling is inline in {f} ({note}; measured 2026-09-10)"


_FINDING = (
    "written, NO stylesheet rule, not inline-styled — finding, tracked on "
    "scitex-ui-shell-components-ship-classes-no-stylesheet-touches-20260910"
)

_KNOWN_UNSTYLED: dict[str, str] = {
    # dead tree (13) — the fork's ts/ half, which emits nothing css/ styles
    "stx-app-file-browser": _DEAD_TREE,
    "stx-app-file-browser__badge": _DEAD_TREE,
    "stx-app-file-browser__chevron": _DEAD_TREE,
    "stx-app-file-browser__chevron--expanded": _DEAD_TREE,
    "stx-app-file-browser__git-badge": _DEAD_TREE,
    "stx-app-file-browser__header": _DEAD_TREE,
    "stx-app-file-browser__item": _DEAD_TREE,
    "stx-app-file-browser__item--active": _DEAD_TREE,
    "stx-app-file-browser__item--directory": _DEAD_TREE,
    "stx-app-file-browser__label": _DEAD_TREE,
    "stx-app-file-browser__symlink": _DEAD_TREE,
    "wft-drag-count": _DEAD_TREE,
    "wft-root-name": _DEAD_TREE,
    # (the wft-breadcrumb* family is NOT ceilinged: it is styled by the dead
    #  tree's own css/shell/workspace-files-tree/ — measured 2026-09-10. The
    #  styled-and-unwritten half of that subtree is the fork card's, not
    #  this guard's. wft-drag-count / wft-root-name ARE unstyled: the first
    #  is written by dead code with an inline cssText, the second sits in a
    #  template attribute whose sibling (wft-name) is styled but it is not.)
    # inline-styled hooks (6)
    "stx-pdf-page": _inline_hook("ts/app/pdf-viewer/index.ts", "10 .style writes"),
    "stx-shell-sketch-overlay": _inline_hook("ts/shell/chat/_sketch-canvas.ts", "19 .style writes"),
    "stx-shell-sketch-panel": _inline_hook("ts/shell/chat/_sketch-canvas.ts", "19 .style writes"),
    "stx-shell-webcam-overlay": _inline_hook("ts/shell/chat/_webcam-capture.ts", "10 .style writes"),
    "stx-shell-webcam-panel": _inline_hook("ts/shell/chat/_webcam-capture.ts", "10 .style writes"),
    "ws-viewer-fallback-pre": _inline_hook("ts/shell/viewer/_ViewerManager.ts", "full rule in pre.style.cssText at :475"),
    # True findings: none. PR #249 corrected the drop-target selector, and
    # PR #255 styled the remaining nine chat classes plus viewer placeholder.
    # The ratchet below now fails every newly emitted unstyled class.
}


# ── tests ───────────────────────────────────────────────────────────────────


def test_extractor_positive_control() -> None:
    """Classes we KNOW are written must be extracted.

    The searchbox class is written by the live react/ tree (FileBrowser.tsx
    className=) and styled by css/app/file-browser/search.css — extracted AND
    covered. wft-breadcrumb proves the CLS-built form is captured (from the
    dead tree, ceilinged — written even though not styled).
    """
    # Arrange
    written = _written_classes()
    # Act
    present = {"stx-app-file-tree__search-box", "wft-breadcrumb"} & set(written)
    # Assert
    assert present == {"stx-app-file-tree__search-box", "wft-breadcrumb"}, (
        "positive control class missing from the written set — the extractor "
        f"regressed; every result in this file is suspect. present: {sorted(present)}"
    )


def test_extractor_negative_control() -> None:
    """Names that are NOT class writes must NOT be extracted.

    Every entry was a measured false positive of the naive 2026-09-10 string
    sweep: element IDs, storage keys, the meta name, an event name, a CSS
    custom property family. If any reappears, a context pattern leaked.
    """
    # Arrange
    written = _written_classes()
    non_classes = {
        "stx-mount": "MOUNT_META_NAME — the wire literal (meta name)",
        "stx-theme": "localStorage key",
        "stx-shell-ai-conversation": "localStorage key",
        "ws-repo-monitor": "getElementById target",
        "stx-shell-ai-chat-view": "getElementById target (ternary branch)",
        "ws-apps-sidebar": "SIDEBAR_IDS array — element IDs",
        "workspace-file-open": "CustomEvent name",
        "stx-app-tooltip-description": "TOOLTIP_ID constant",
        "stx-verdict-": "CSS custom property family (--stx-verdict-${key})",
    }
    # Act
    leaked = {c: why for c, why in non_classes.items() if c in written}
    # Assert
    assert not leaked, (
        "non-class strings entered the written set — the extractor is matching "
        "beyond class-assignment contexts: "
        + "; ".join(f"{c} ({w})" for c, w in sorted(leaked.items()))
    )


def test_written_set_floor() -> None:
    """The written population must be plausibly large.

    2026-09-10 measured 235 context-verified class writes (a naive string
    sweep read 261; 26 of those were non-classes). A floor of 200 keeps an
    ~15% collector drift loud. `assert written` (non-emptiness) would pass on
    a broken collector returning 1 — the exact defect this guard's sibling
    shipped with, measured at 1 of 120.
    """
    # Arrange: the checkout IS the fixture
    # Act
    n = len(_written_classes())
    # Assert
    assert n >= 200


def test_styled_set_floor() -> None:
    """The styled population must be plausibly large (450+ namespaced, more
    unrestricted, measured 2026-09-10). Guards against the CSS side of the
    comparison vanishing, which would turn EVERY written class into a
    "finding" and read as a mass defect rather than a broken scan."""
    # Arrange: the checkout IS the fixture
    # Act
    n = len(_styled_classes())
    # Assert
    assert n >= 400


def test_every_written_class_is_styled_or_ceilinged() -> None:
    """THE GUARD. A namespaced class written by live code must be covered by
    css/ or sit on _KNOWN_UNSTYLED with a written reason."""
    # Arrange
    written = _written_classes()
    styled = _styled_classes()
    # Act
    candidates = {
        c: locs
        for c, locs in written.items()
        if not _covered(c, styled) and c not in _KNOWN_UNSTYLED
    }
    # Assert
    assert not candidates, (
        "classes written by this package that no stylesheet touches (and are "
        "not on the reasoned ceiling) — either style them, or add them to "
        "_KNOWN_UNSTYLED with a MEASURED reason (inline-styled hook / dead "
        "tree / finding-with-card). Do not add an entry to make this green:\n"
        + "\n".join(
            f"  {c}  <- {sorted(locs)[0]}" for c, locs in sorted(candidates.items())
        )
    )


def test_ceiling_entries_still_unstyled() -> None:
    """Staleness ratchet (the consumer guard's shape): a ceiling entry whose
    class acquires a stylesheet rule is a fixed defect wearing an exemption.
    Remove the entry when you style the class — this fails until you do."""
    # Arrange
    styled = _styled_classes()
    # Act
    stale = sorted(c for c in _KNOWN_UNSTYLED if _covered(c, styled))
    # Assert
    assert not stale, (
        "these ceiling entries are now STYLED — the debt is paid; remove them: "
        + ", ".join(stale)
    )


def test_ceiling_entries_still_written() -> None:
    """The other rot direction: a ceiling entry whose code is DELETED is a
    finding that no longer exists (or a dead tree that was finally removed).
    Prune the entry when the source goes — this fails until it is."""
    # Arrange
    written = _written_classes()
    # Act
    stale = sorted(c for c in _KNOWN_UNSTYLED if c not in written)
    # Assert
    assert not stale, (
        "these ceiling entries are no longer WRITTEN anywhere — prune them: "
        + ", ".join(stale)
    )


# ── detector controls ───────────────────────────────────────────────────────
# test_detectors_carry_controls.py requires every module-level detector to
# prove BOTH directions on LITERAL samples: it can fire, and it does not fire
# on a near-miss. The negatives below are the near-misses a string-keyed
# detector gets wrong — the 26 false positives of the 2026-09-10 calibration
# sweep, one per extraction context.


def test_re_classname_q_matches_a_real_write() -> None:
    # Arrange
    sample = 'wrap.className = "stx-pdf-page";'  # pdf-viewer/index.ts:177
    # Act
    matched = _RE_CLASSNAME_Q.search(sample)
    # Assert
    assert matched is not None


def test_re_classname_q_ignores_a_mention() -> None:
    # Arrange
    sample = '// className is set to "stx-pdf-page" at runtime'
    # Act
    matched = _RE_CLASSNAME_Q.search(sample)
    # Assert
    assert matched is None


def test_re_classname_t_matches_a_real_write() -> None:
    # Arrange
    sample = 'code.className = `language-${language}`;'  # ViewerManager.ts:478
    # Act
    matched = _RE_CLASSNAME_T.search(sample)
    # Assert
    assert matched is not None


def test_re_classname_t_ignores_a_mention() -> None:
    # Arrange
    sample = "backtick className templates like `x--${k}` are open-ended"
    # Act
    matched = _RE_CLASSNAME_T.search(sample)
    # Assert
    assert matched is None


def test_re_classlist_matches_a_real_write() -> None:
    # Arrange
    sample = 'container.classList.add("stx-shell-drop-target");'  # _TerminalFactory.ts:284
    # Act
    matched = _RE_CLASSLIST.search(sample)
    # Assert
    assert matched is not None


def test_re_classlist_ignores_a_contains_call() -> None:
    """contains is a READ, not a write — the near-miss a string-keyed scan hits."""
    # Arrange
    sample = 'container.classList.contains("stx-shell-drop-target");'
    # Act
    matched = _RE_CLASSLIST.search(sample)
    # Assert
    assert matched is None


def test_re_html_class_matches_a_real_write() -> None:
    # Arrange
    sample = '<div class="ws-viewer-placeholder">'  # ViewerManager.ts:257
    # Act
    matched = _RE_HTML_CLASS.search(sample)
    # Assert
    assert matched is not None


def test_re_html_class_ignores_a_js_classname() -> None:
    # Arrange
    sample = 'wrap.className = "stx-pdf-page";'
    # Act
    matched = _RE_HTML_CLASS.search(sample)
    # Assert
    assert matched is None


def test_re_family_matches_a_real_write() -> None:
    # Arrange
    sample = "stx-app-receipt--${s}"  # _Receipt.ts:70
    # Act
    matched = _RE_FAMILY.search(sample)
    # Assert
    assert matched is not None


def test_re_family_ignores_a_non_namespaced_shape() -> None:
    # Arrange
    sample = "the family form base--${kind} is open-ended"
    # Act
    matched = _RE_FAMILY.search(sample)
    # Assert
    assert matched is None


def test_re_quoted_ns_matches_a_real_write() -> None:
    # Arrange
    sample = 'classList.add("stx-shell-drop-target")'
    # Act
    matched = _RE_QUOTED_NS.search(sample)
    # Assert
    assert matched is not None


def test_re_quoted_ns_ignores_an_unquoted_mention() -> None:
    # Arrange
    sample = "use stx-shell-drop-target as the drag class"
    # Act
    matched = _RE_QUOTED_NS.search(sample)
    # Assert
    assert matched is None
