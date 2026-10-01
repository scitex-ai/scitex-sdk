#!/usr/bin/env python3
"""Contract assertions a CONSUMER runs in its own test suite.

``standalone_shell.html`` provides no route back to a launcher unless the
composer supplies one (see :func:`scitex_sdk.ui.branding.shell_context`). That is
the right split — only a mounting platform knows where its launcher lives — but
it means an app can mount through the shell, supply no ``launcher=``, carry no
navigation of its own, and ship a page a visitor cannot leave. Nothing fails.
The page returns 200.

This module is where that absence becomes loud, and it deliberately lives HERE
rather than in the shell:

    THE SHELL CANNOT SEE IT.  ``shell_context()`` runs in the VIEW, building a
    context dict before any template renders. The mounted app's content does
    not merely belong to someone else at that moment — it does not exist yet.
    There is nothing to count.

    THE CONSUMER'S TEST CAN.  By the time a consumer asserts on a rendered
    response, the app's content HAS rendered, so the thing invisible from
    inside ``shell_context`` is sitting right there as a string.

Usage in the consumer's suite::

    from scitex_sdk.ui.testing import assert_has_route_away

    def test_storage_page_is_escapable(client):
        response = client.get("/apps/storage/")
        assert_has_route_away(response.content.decode(), current_path="/apps/storage/")

WHY NOT A RUNTIME WARNING, since that was the first design and it was wrong.
The obvious guard is "warn when the shell renders with no launcher slot". That
predicate is TRUE for ``/apps/cards/`` and ``/apps/storage/`` alike — cards
supplies no launcher either and is perfectly navigable, because its own content
carries links. A developer integrating cards would get a warning about a page
that works, learn the warning is unreliable, and then disbelieve it for storage.
scitex-hub rejected the predicate on exactly this ground, using the control from
their own measurement, and they were right.

WHY "HAS AN ANCHOR" IS ALSO THE WRONG PREDICATE, which is the subtler trap and
the reason this module counts what it counts. scitex-hub measured live prod on
2026-08-23:

    /apps/cards/      6 anchors    navigable
    /apps/storage/    1 anchor     still a dead end

A guard asserting ``count(<a>) >= 1`` PASSES storage. It would have been green
on the exact page that prompted this work — a check that cannot fail on the case
it was built for. One anchor and zero anchors are the same defect to a visitor
when that anchor goes nowhere, so the predicate has to be *routes away*, not
*anchors present*.
"""

from __future__ import annotations

import html.parser
from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "RouteAwayReport",
    "find_routes_away",
    "assert_has_route_away",
    "find_untranslated",
    "assert_no_untranslated",
]

#: ``href`` schemes that never navigate the visitor anywhere.
_INERT_SCHEMES = ("javascript:", "data:", "vbscript:")


@dataclass(frozen=True)
class RouteAwayReport:
    """What a page offers a visitor who wants OUT.

    A fixed shape with each signal named, so a caller never has to guess which
    key this call happened to return.

    :param routes: hrefs that would actually take the visitor elsewhere.
    :param rejected: ``(href, reason)`` for every anchor that does not, so a
        failure can say *why* the four links on the page do not count.
    :param anchors_total: every ``<a>`` seen, routing or not. Kept because
        ``anchors_total > 0 and not routes`` is the interesting state — the page
        looks linked and is not.
    """

    routes: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]
    anchors_total: int

    @property
    def has_route_away(self) -> bool:
        return bool(self.routes)


class _AnchorCollector(html.parser.HTMLParser):
    """Collect every ``<a>`` start tag's ``href`` (or its absence)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        # Only the FIRST href counts: that is what a browser honours when a
        # malformed tag repeats the attribute.
        for name, value in attrs:
            if name == "href":
                self.hrefs.append(value if value is not None else "")
                return
        self.hrefs.append(None)


def _classify(href: str | None, current_path: str | None) -> str | None:
    """Return the reason ``href`` is NOT a route away, or ``None`` if it is."""
    if href is None:
        # <a> with no href at all is not a link: browsers give it no default
        # role and no keyboard focus. It renders like text.
        return "no href attribute"

    target = href.strip()
    if not target:
        return "empty href"
    if target.startswith("#"):
        return "in-page fragment"
    if target.lower().startswith(_INERT_SCHEMES):
        return "non-navigating scheme"
    if current_path is not None and target == current_path:
        return "self-link (same as current_path)"
    return None


def find_routes_away(
    rendered_html: str,
    *,
    current_path: str | None = None,
) -> RouteAwayReport:
    """Report the routes a rendered page offers away from itself.

    :param rendered_html: the RENDERED page, not a template.
    :param current_path: the path this page was served at. Supplied, an anchor
        pointing right back at it is rejected as a self-link. Omitted, self-links
        are counted — the check is weaker, and deliberately not silently so: pass
        the path when you know it.
    :raises ValueError: if ``rendered_html`` is empty or whitespace.

    Empty input RAISES rather than returning "no routes found". They are
    different answers — one is a page with no way out, the other is a test that
    fetched nothing — and collapsing them would let a broken fixture read as a
    real finding.
    """
    if not rendered_html or not rendered_html.strip():
        raise ValueError(
            "rendered_html is empty. This is a fixture problem, not a finding: "
            "an empty string cannot tell you whether a page has a route away. "
            "Check that the response actually rendered and was decoded."
        )

    collector = _AnchorCollector()
    collector.feed(rendered_html)
    collector.close()

    routes: list[str] = []
    rejected: list[tuple[str, str]] = []
    for href in collector.hrefs:
        reason = _classify(href, current_path)
        if reason is None:
            assert href is not None  # _classify rejects None
            routes.append(href.strip())
        else:
            rejected.append((href if href is not None else "", reason))

    return RouteAwayReport(
        routes=tuple(routes),
        rejected=tuple(rejected),
        anchors_total=len(collector.hrefs),
    )


def assert_has_route_away(
    rendered_html: str,
    *,
    current_path: str | None = None,
) -> RouteAwayReport:
    """Assert a rendered page offers the visitor at least one way out.

    Returns the :class:`RouteAwayReport` on success, so a caller can make a
    sharper assertion afterwards (e.g. that one route points at the launcher).

    :raises AssertionError: when the page offers no route away. The message
        names every anchor that was rejected and why, because "no route away"
        on a page with four links is otherwise baffling.
    :raises ValueError: if ``rendered_html`` is empty (see
        :func:`find_routes_away`).
    """
    report = find_routes_away(rendered_html, current_path=current_path)
    if report.has_route_away:
        return report

    lines = [
        "This page offers no route away: a visitor who lands here has nothing "
        "to click that leaves.",
        f"  anchors found: {report.anchors_total}",
    ]
    if report.rejected:
        lines.append("  every anchor was rejected:")
        lines.extend(f"    {href!r}: {why}" for href, why in report.rejected)
    else:
        lines.append("  the page contains no <a> elements at all.")
    lines.append(
        "  Fix: pass launcher={'url': ..., 'label': ...} to "
        "scitex_sdk.ui.branding.shell_context(), or give the app its own navigation."
    )
    raise AssertionError("\n".join(lines))


# ── Translation completeness ────────────────────────────────────────────────

#: Attributes whose values a visitor reads or hears, so they must be translated too.
_VISIBLE_ATTRIBUTES = ("title", "placeholder", "aria-label", "alt")

#: Never shown; a json_script catalog holds English msgids as its keys.
_INVISIBLE_ELEMENTS = ("script", "style", "template", "noscript")


class _VisibleTextCollector(html.parser.HTMLParser):
    """Collect whitespace-normalised text nodes and visible attribute values."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.texts: set[str] = set()
        self._invisible_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _INVISIBLE_ELEMENTS:
            self._invisible_depth += 1
        for name, value in attrs:
            if name in _VISIBLE_ATTRIBUTES and value:
                self.texts.add(" ".join(value.split()))

    def handle_endtag(self, tag: str) -> None:
        if tag in _INVISIBLE_ELEMENTS and self._invisible_depth:
            self._invisible_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._invisible_depth:
            self.texts.add(text)


def find_untranslated(rendered_html: str, english_strings: Iterable[str]) -> list[str]:
    """Return the strings from ``english_strings`` still shown verbatim in ``rendered_html``.

    A string counts only as a whole text node or a whole title/placeholder/
    aria-label/alt value, so "Save" does not match inside "Saved".
    """
    if not rendered_html or not rendered_html.strip():
        raise ValueError("rendered_html is empty; the page did not render.")
    collector = _VisibleTextCollector()
    collector.feed(rendered_html)
    collector.close()
    return [text for text in english_strings if " ".join(text.split()) in collector.texts]


def assert_no_untranslated(rendered_html: str, english_strings: Iterable[str]) -> None:
    """Assert a translated render shows none of ``english_strings`` verbatim."""
    leftovers = find_untranslated(rendered_html, english_strings)
    if leftovers:
        raise AssertionError(
            "Untranslated strings on the rendered page:\n"
            + "\n".join(f"  {text!r}" for text in leftovers)
        )
