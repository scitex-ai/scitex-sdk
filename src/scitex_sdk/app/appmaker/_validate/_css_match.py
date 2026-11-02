#!/usr/bin/env python3
"""WHETHER A SELECTOR TARGETS A PROTECTED NAME — the matching layer.

Split out of `_css.py` on 2026-09-06. EVERY DEFECT OF 2026-09-05/06 LIVED
HERE, which is the argument for the split: a `:not()` argument read as a
target, a word boundary that made every exact name behave like a prefix,
one rule reported twice under two nested names, and a boundary that then
stopped matching BEM modifiers the shell really renders.

The tables in `_css_tables.py` are wrong when hub's tree changes. This file
is wrong when I reason about strings badly, and it has been, four times.
"""

from __future__ import annotations

import re

#: TIER 2 — the shell's own footer element, by measurement and by compromise.
#:
#: `#site-footer` is TIER 1 above: 3 shell-side renders, ZERO app-side.
#: A BARE `footer` element selector is different and the honest rule would be
#: tier 1 — such a selector CANNOT be scoped to the app's own node, so it
#: reaches the shell's `<footer>` by construction. scitex-hub measured one app
#: legitimately rendering its own (`public_app public_status.html:73`,
#: `<footer class="status-footer">`), confirmed by a shell comment saying the
#: workspace page hides `.site-footer` so a page may carry its own legal line.
#:
#: (a) IS NOT IMPLEMENTABLE BY SUBSTRING, which is why this is (b). Banning the
#: token `footer` cannot tell the selector `footer` from `.status-footer`,
#: `.site-footer` or `--footer-height` — it would flag that app's correct
#: class. That is tier 3's problem wearing a different hat.
#:
#: RESIDUAL RISK, declared in `not_checked` rather than left implicit: an app
#: writing `footer { color: red }` WITHOUT `!important` restyles the shell's
#: footer and this rule does not see it. Revisit when the parser lands.
#: LEFTMOST position only — `footer` starting a selector, or following a comma.
#: `.myapp footer` is SCOPED to the app's own subtree and cannot reach the
#: shell's element, so it is correct code and must not report. Measured: the
#: first version matched any position and flagged `.myapp footer { ... }`,
#: which is exactly the false-positive class this whole rule exists to avoid.
#:
#: This is PARTIAL scope detection and it does not generalise. "Is `footer` the
#: leftmost token" is answerable by substring; "is the leftmost token the APP'S
#: OWN root" is tier 3 and is not. It removes one specific false positive, not
#: the class.
_FOOTER_ELEMENT = re.compile(r"(^|,)\s*footer(?![\w-])")

#: Blank the ARGUMENTS of functional pseudo-classes before the leftmost test.
#:
#: `:is(header, footer) .x` puts `footer` after a COMMA, so the leftmost rule
#: reads it as a second selector in a list and fires. It is not one — it is an
#: argument, and `:is()` / `:not()` / `:where()` / `:has()` all take selector
#: lists whose commas are internal. `:not(footer)` is the sharpest case: the
#: rule EXCLUDES a footer and the detector called that targeting one.
#:
#: scitex-hub found this against 0.14.4 in `public_app/css/pricing.css`
#: (`body > :first-child:not(header):not(main):not(footer)`), which the
#: canonical already passed — `(` is not a boundary. The hole was in the
#: HYPOTHETICAL they offered beside it, `:is(header, footer)`, which fires.
#: Their concrete example was already handled and their generalisation was
#: right anyway; measuring both is what separated them.
#:
#: Blanking rather than deleting keeps offsets and the leftmost/`,` structure
#: intact, so nothing else shifts under the test.
_PSEUDO_ARGS = re.compile(r"\(([^()]*)\)")


def _strip_pseudo_args(selector: str) -> str:
    """Replace the contents of every parenthesised group with spaces. Applied
    repeatedly so nested groups (`:has(:not(footer))`) collapse from the inside
    out.

    FOR THE LEFTMOST TEST ONLY. It answers a STRUCTURAL question — "does this
    selector list begin with a bare `footer`?" — for which every internal comma
    is noise regardless of which pseudo-class it sits in. Do not reach for it
    to answer the membership question below; see `_strip_excluded` for why the
    two cannot share one stripper.
    """
    previous = None
    while previous != selector:
        previous = selector
        selector = _PSEUDO_ARGS.sub(lambda m: "(" + " " * len(m.group(1)) + ")", selector)
    return selector


#: `:not(X)` EXCLUDES X and `:has(X)` makes X a condition on an ancestor. In
#: neither is X styled, so a protected name appearing there is not a target.
_EXCLUDED_ARG = re.compile(r":(?:not|has)\([^()]*\)", re.IGNORECASE)


def _strip_excluded(selector: str) -> str:
    """Blank `:not(...)` and `:has(...)` whole, repeatedly so nesting collapses
    from the inside out.

    DELIBERATELY NOT `_strip_pseudo_args`, AND THIS IS THE OPPOSITE OF THE
    USUAL LESSON. Two strippers here are not one rule implemented twice: they
    answer two different questions, and collapsing them breaks one of the two.

        membership  "is this protected name a TARGET of this rule?"
                    `:not(.panel-resizer)` excludes it     -> not a target
                    `:is(.foo, .h-resizer)` MATCHES it     -> IS a target
        leftmost    "does this selector list begin with a bare `footer`?"
                    every internal comma is noise, `:is()` included

    So membership must keep `:is()` / `:where()` contents and drop `:not()` /
    `:has()`; the leftmost test must drop all four. Blanking everything for
    membership would silently stop reporting `:is(.foo, .h-resizer)
    {!important}`, which really does style the shell's resizers.

    scitex-hub proposed `:is(.foo, .h-resizer)` and `:where(.stx-shell-sidebar)`
    as must-NOT-fire cases alongside their `:not()` finding. The `:not()` half
    was right and is fixed here; the `:is()` half is not — `:is()` is a
    matching pseudo-class, and treating it like `:not()` would have converted
    their false positive into a false negative.
    """
    previous = None
    while previous != selector:
        previous = selector
        selector = _EXCLUDED_ARG.sub(lambda m: " " * len(m.group(0)), selector)
    return selector


#: A BEM MODIFIER BELONGS TO ITS BLOCK; A TRAILING WORD IS A DIFFERENT NAME.
#:
#: `.stx-shell-sidebar--collapsed` is the SAME component in a state — the shell
#: renders it (_Sidebar.ts:85, :103) — so an app `!important`ing it reaches a
#: real shell node. `.stx-shell-sidebar__header-compact` is a DIFFERENT element
#: that writer minted inside the namespace and the shell renders none of.
#:
#: The plain `(?![\w-])` boundary of 0.15.2 excluded BOTH, because the
#: difference between them is not in the string — it is whether the shell
#: renders it, a fact about hub's tree. So the grammar handles only the half a
#: string CAN decide:
#:
#:     ELEMENTS   named and enumerable -> they are TABLE ENTRIES. An element
#:                the table lacks is a TABLE gap, and widening the grammar to
#:                `__[\w-]+` to cover it would re-admit `__header-compact`.
#:     MODIFIERS  open-ended state, added freely -> GRAMMAR. Any table entry
#:                may carry `--anything`.
#:
#: MEASURED by scitex-ui 2026-09-06, at my request via hub, after their FIRST
#: scan returned zero and they declined to report it because the asymmetry
#: looked implausible — the classes are built with template literals
#: (`${CLS}--collapsed`), invisible to a literal-string search. Had that zero
#: been reported I would have kept the boundary.
_BEM_MODIFIER = r"(?:--[\w-]+)?"


def _matched_names(selector: str, names: tuple[str, ...]) -> list[str]:
    """Which of `names` this selector actually SELECTS — not which it contains.

    TWO CORRECTIONS TO `name in selector`, both found by scitex-hub's second
    step-2 run against their own tree (0.15.1, `develop@4ec9c4066`), and both
    of which they attributed to their own code rather than to this rule.

    ONE — A LONGER CLASS NAME IS A DIFFERENT CLASS. `.stx-shell-sidebar__header`
    and `.stx-shell-sidebar__header-compact` are unrelated selectors; a rule on
    the second cannot touch the first. `in` said otherwise, so writer's eight
    `__header-compact` rules were reported as styling `__header`. hub read that
    as "writer minted a class inside the shell's BEM namespace" — true, and a
    fair thing to raise with writer, but NOT what the finding said. The finding
    named a class the selector does not contain.

        `-` is a legal class-name character, so the trailing guard is
        `(?![\\w-])` — the same boundary the footer rule already used and this
        one did not. The LEADING side needs no guard: `.foo` cannot occur
        inside `.my-foo`, because the `.` is part of the token.

        SHELL_INSTANCE_PREFIXES are exempt and stay substring matches. Those
        are prefix FAMILIES by construction — `.wft-` is meant to match
        `.wft-node` — which is exactly the distinction `in` erased.

    TWO — ONE RULE, ONE FINDING. `.stx-shell-sidebar` and
    `.stx-shell-sidebar__header` are BOTH in `SHARED_COMPONENT_CLASSES`, and
    both substring-matched the same selector, so a single declaration produced
    two findings under two names. That inflates any count taken from this rule
    — hub's eight were four rules — and a count that inflates is worse than one
    that is merely incomplete, because it reads as MORE evidence.

        A name that is a proper substring of another matched name is dropped:
        the most specific match is the one that describes the selector. Two
        genuinely different names (`.panel-resizer, .h-resizer`) still report
        twice, because neither contains the other.
    """
    hits = [
        n
        for n in names
        if re.search(rf"{re.escape(n)}{_BEM_MODIFIER}(?![\w-])", selector)
    ]
    return [n for n in hits if not any(n != m and n in m for m in hits)]


def _rule_blocks(content: str):
    """(selector, body, line) for each top-level rule. Not a parser — see the
    module docstring. Enough to attribute a declaration to the selector it sits
    under, which is all tiers 1 and 2 need.

    `line` is 1-based and points at the selector, so a reader can go straight
    to the rule instead of searching the file for a class name that may occur
    in several. scitex-hub had to hunt for one and landed on a nearby rule that
    merely looked like the reported one."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", content, re.DOTALL):
        yield m.group(1).strip(), m.group(2), content.count("\n", 0, m.start(1)) + 1


#: margin/padding declaration names, longhands included (`margin-inline`).
_MARGIN_PADDING_PROP = re.compile(r"^(margin|padding)(-[a-z]+)?$", re.IGNORECASE)

#: A static length. Unitless zero carries no unit; anything else unitless is
#: invalid CSS for these properties and not this rule's job.
_LENGTH = re.compile(
    r"([-+]?(?:\d+\.?\d*|\.\d+))"
    r"(px|em|rem|cap|ch|ex|ic|lh|rlh|vw|vh|vi|vb|vmin|vmax|"
    r"cqw|cqh|cqi|cqb|cqmin|cqmax|cm|mm|q|in|pt|pc|%)",
    re.IGNORECASE,
)

#: `auto` centers instead of spacing; on the app box that still insets the
#: largest content. `inherit`/`unset`/`revert` hand the value to the shell or
#: the UA, which is the defect by delegation. `initial` computes to zero and
#: stays silent with the resets.
_AUTO_OR_DELEGATED = re.compile(r"\b(auto|inherit|unset|revert)\b", re.IGNORECASE)


def _declarations(body: str):
    """(property, value) pairs of one rule body, lowercased property names."""
    for chunk in body.split(";"):
        if ":" not in chunk:
            continue
        prop, _, value = chunk.partition(":")
        yield prop.strip().lower(), value


def _margin_padding_offense(value: str) -> bool:
    """Whether a margin/padding value insets the box it is set on.

    Zero in any unit is a compliant reset. A bare `var()`/`env()` with no
    literal length is invisible to a static read — declared in
    `not_checked` rather than guessed at. A literal inside a fallback
    (`var(--x, 8px)`, `calc(... + 24px)`) IS read: the fallback is the
    value wherever the token is unpublished.
    """
    lowered = value.lower()
    for match in _LENGTH.finditer(lowered):
        if float(match.group(1)) != 0:
            return True
    return bool(_AUTO_OR_DELEGATED.search(lowered))


def _subject_names(selector_list: str, names: tuple[str, ...]) -> list[str]:
    """Which of `names` is the SUBJECT of some selector in the list.

    Membership (`_matched_names`) is the wrong test here: `#main-content
    .mine` mentions the container but styles the child. Only a name in the
    last compound of a selector gets that rule's declarations, so only
    those fire. Comma splitting runs on the `:not`/`:has`-blanked targets;
    a comma inside `:is()`/`:where()` splits mid-selector, but the fragment
    carrying the container still ends with it, so the verdict is unchanged.
    """
    found: list[str] = []
    for part in selector_list.split(","):
        compounds = [c for c in re.split(r"[\s>+~]+", part.strip()) if c]
        if not compounds:
            continue
        subject = compounds[-1]
        for name in names:
            if re.search(rf"{re.escape(name)}{_BEM_MODIFIER}(?![\w-])", subject):
                if name not in found:
                    found.append(name)
    return found


# EOF
