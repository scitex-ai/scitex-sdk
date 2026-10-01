#!/usr/bin/env python3
"""Shared SciTeX GUI branding: tab title convention + brand favicon.

Before this module each tool hand-rolled its own tab branding, so the fleet
drifted: some tabs showed the generic browser globe, and titles read
"FigRecipe Editor" / "SciTeX Writer" / "default-project — SciTeX".

The convention is:

* **Title** — ``"SciTeX <Tool>"`` (SciTeX Writer, SciTeX Scholar, SciTeX
  FigRecipe, SciTeX Todo). :func:`shell_title` normalises a tool name into
  that form and is idempotent, so passing ``"SciTeX Writer"`` is also fine.
* **Favicon** — the shared brand mark at ``scitex_sdk/ui/img/scitex-favicon.svg``,
  rendered whenever a view supplies no ``favicon_href``.

Usage in a view::

    from scitex_sdk.ui.branding import shell_context

    def index(request):
        return render(request, "myapp/index.html", {
            **shell_context("Storage", accent="storage"),
            ...,
        })

**Adopting the shared mark means DELETING your workaround, not just
upgrading.** An existing ``favicon_href`` — or your own ``<link rel="icon">``
in ``extra_css`` — wins, deliberately: an app that wants its own mark must be
able to keep it. But that means upgrading alone changes nothing, and the tab
still shows the old icon. It renders *a* favicon, which is not the same as
rendering *the* mark, and nothing warns you. At 0.7.1 three of the four
shell-extending GUIs were in exactly that state. To adopt: remove the
``favicon_href`` key from your context, or delete the local link tag.

**The shell emits exactly ONE ``<link rel="icon">``.** Setting ``favicon_href``
while keeping your existing tag moves the duplicate rather than removing it.
Sized variants (``rel="icon" sizes="32x32"``) and ``apple-touch-icon`` cannot be
expressed here and belong in your own ``extra_css`` — the shell owns the single
primary icon, the app owns the rest.

**Not every GUI renders this shell.** These helpers assume
``standalone_shell.html``; a GUI that owns its own layout can still get the
mark via ``{% include "scitex_sdk/ui/_branding_head.html" %}`` in its own
``<head>``, with no shell adoption and no layout migration.
"""

from __future__ import annotations

BRAND = "SciTeX"

#: Static path of the shared brand mark, relative to the staticfiles root.
FAVICON_STATIC_PATH = "scitex_sdk/ui/img/scitex-favicon.svg"


def shell_title(tool: str) -> str:
    """Return the tab title for ``tool`` in the ``"SciTeX <Tool>"`` convention.

    Idempotent: a name that already carries the brand prefix is returned
    unchanged, so callers can pass either ``"Writer"`` or ``"SciTeX Writer"``.
    An empty/blank name degrades to the bare brand rather than ``"SciTeX "``.
    """
    name = (tool or "").strip()
    if not name:
        return BRAND
    if name == BRAND or name.startswith(f"{BRAND} "):
        return name
    return f"{BRAND} {name}"


#: Panes an app may declare. See :func:`shell_context`'s ``panes`` parameter.
PANE_NAMES = ("ai", "files", "viewer")

#: What an app may declare a pane to BE. Declared, never inferred.
#:
#: ``"unused"``
#:     the app does not use this pane at all — collapse it and give the app's
#:     content the width back.
#:
#: ``"client-populated"``
#:     the pane IS used, but its content arrives after mount, so it is
#:     legitimately empty at render time.
#:
#: ``"used"``
#:     the pane is populated server-side.
#:
#: Only ``"unused"`` changes the layout. The other two are equivalent today and
#: both mean "leave it alone"; they are distinct because they say different
#: things about the app, and a future change may care about the difference.
PANE_STATES = ("unused", "client-populated", "used")

#: Exactly the keys ``shell_context(launcher=...)`` accepts. A set rather than a
#: tuple because both directions are checked — missing keys AND unknown ones —
#: so a caller who writes ``{"href": ...}`` is told, instead of getting a page
#: with no link and no explanation.
_LAUNCHER_KEYS = {"url", "label"}


def _active_language() -> str:
    """The language Django has active for this request, or ``"en"``.

    ``get_language()`` returns ``None`` when translations are deactivated, so
    the fallback is not decoration — without it the attribute would render
    empty, and an empty ``lang=""`` is worse than a wrong one: a screen reader
    then has no rule to apply at all rather than the wrong rule.

    Imported lazily because ``branding`` is imported by code paths that have not
    configured Django, and a module-scope import of ``django.utils.translation``
    would make those paths fail on an attribute this package can default.
    """
    try:
        from django.utils.translation import get_language
    except Exception:  # Django absent or not configured
        return "en"
    return get_language() or "en"


def shell_context(
    tool: str,
    *,
    accent: str | None = None,
    favicon_href: str | None = None,
    theme_default: str = "dark",
    lang: str | None = None,
    panes: dict[str, str] | None = None,
    launcher: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build a ``standalone_shell.html`` context.

    :param tool: tool name, with or without the ``SciTeX`` prefix.
    :param accent: value for the shell's ``data-app-accent`` (e.g. ``"storage"``);
        must have a mapping row in ``css/shell/stx-shell-sidebar.css``.
    :param favicon_href: explicit override. Left out, the shell falls back to the
        shared brand mark — which is what almost every tool should do. Note that
        supplying one means the shared mark never renders for your app.
    :param theme_default: theme used when the visitor has no stored preference.
        Dark by default; a stored preference always wins (see ``_theme_boot``).
    :param lang: BCP-47 tag for ``<html lang>``. Left out, the shell uses the
        language Django has ACTIVE for this request, falling back to ``"en"``.

        **Why this one is detected rather than declared**, against the rest of
        this API. Panes and accents are CHOICES an app makes, so they are
        declared and a typo raises. The page language is not a choice the shell
        gets to make — Django has already resolved it from the request, and a
        second place to state it is a second place to be wrong. Requiring every
        leaf to pass it would reproduce the bug this parameter fixes: four
        leaves inheriting a value nobody remembered to set.
    :param panes: what each pane IS, e.g. ``{"ai": "unused", "files": "unused"}``.
        Keys from :data:`PANE_NAMES`, values from :data:`PANE_STATES`. Omitted
        panes are left visible.
    :param launcher: where to send someone who wants OUT of this app, e.g.
        ``{"url": "/apps/store/", "label": "Apps"}``. Both keys required.
        Omitted, the shell renders no such link at all.

    **Why the destination is supplied rather than assumed.** The obvious
    implementation — hardcode a link to ``/`` — is wrong, and wrong in the mode
    this shell is named for. Per the dual-mode contract, a STANDALONE app is
    mounted AT ``/``; a link there points at the app's own root, which is a
    self-link, not an escape. Only a mounting platform knows where its launcher
    lives, so only it can say.

    Nor can the shell detect which mode it is in and decide for itself:
    ``_mount_marker.html`` renders only when a view merged ``mount_context``,
    which is optional, and ``mount_prefix()`` deliberately raises rather than
    guess a root mount. Inferring here would undermine the one refusal the
    mount contract is built on.

    So the split is: this package owns the SLOT — markup, styling, placement,
    and the rule that it renders if and only if given a destination — and the
    composer owns the DESTINATION. A standalone app supplies nothing and
    correctly gets no link, because there is nowhere to go back to.

    **THE SHELL PROVIDES NO ROUTE BACK ON ITS OWN, AND CANNOT CHECK THAT YOU
    SUPPLIED ONE.** A MOUNTED app that passes no ``launcher`` and carries no
    navigation of its own ships a page a visitor cannot leave; nothing here
    fails, and the page returns 200. This function cannot detect it — it runs in
    the VIEW, and the mounted app's content does not exist yet, so there is
    nothing to count.

    Assert it in your own suite instead, where the page HAS rendered::

        from scitex_sdk.ui.testing import assert_has_route_away

        def test_storage_page_is_escapable(client):
            page = client.get("/apps/storage/").content.decode()
            assert_has_route_away(page, current_path="/apps/storage/")

    Note it checks for a route that LEAVES, not for the presence of an ``<a>``:
    scitex-hub measured ``/apps/storage/`` with one anchor that went nowhere, so
    an anchor count reads that dead end as healthy.

    Raised by scitex-hub 2026-08-19 after measuring live prod at 390x844:
    ``/apps/storage/`` had ZERO anchor elements — nothing on the page a visitor
    could click to leave. Their control settles that it is this shell's defect
    rather than one app's: ``/apps/cards/`` mounts the same way and has three
    links, but they come from cards' own content, and BOTH report zero links to
    the root. So the shell supplies no route out to anything mounted through
    it, and storage is simply the app whose own content does not compensate.

    **Why panes are declared rather than detected.** Two reasons.

    1. Apps were reaching into the shell's internals instead. scitex-writer hid
       these panes with a stylesheet targeting
       ``.workspace-three-col > .ws-ai-pane`` and siblings — private class names
       this package is free to rename, which would have broken them silently
       and invisibly to both sides. A declaration is an API the shell is
       obliged not to break; a stylesheet aimed at its DOM is not.
    2. "Collapse a pane with no content" would measure the wrong thing anyway.
       A pane filled by JS after mount has no content at render time either, so
       emptiness is uncorrelated with whether the pane matters. This is a
       property of client-side rendering, not a claim about any one app.

    Only the app knows which of its panes it uses, so the app says.

    Opt-in for the same reason: forgetting to declare leaves the page exactly as
    it is today, while an opt-out default that guessed wrong would hide a
    working pane. The failure mode of forgetting must be invisible, not
    destructive.

    Keys are omitted rather than set to ``None`` so they cannot shadow a value
    a caller merged in earlier.

    :raises ValueError: on an unknown pane name or state. A typo must fail
        loudly here rather than silently leaving a pane visible, which would
        look identical to not having declared it at all.
    """
    context: dict[str, object] = {
        "app_label": shell_title(tool),
        "shell_theme_default": theme_default,
        "shell_lang": lang or _active_language(),
    }
    if accent:
        context["app_accent"] = accent
    if favicon_href:
        context["favicon_href"] = favicon_href
    if panes:
        for name, state in panes.items():
            if name not in PANE_NAMES:
                raise ValueError(
                    f"unknown pane {name!r}; expected one of {PANE_NAMES}"
                )
            if state not in PANE_STATES:
                raise ValueError(
                    f"unknown state {state!r} for pane {name!r}; "
                    f"expected one of {PANE_STATES}"
                )
        context["panes"] = dict(panes)
    if launcher:
        context.update(launcher_context(launcher))
    return context


def launcher_context(launcher: dict[str, str]) -> dict[str, object]:
    """Validate a launcher destination and return it as a template context.

    ``{"url": ..., "label": ...}`` in, ``{"launcher": {...}}`` out.

    **Use this rather than :func:`shell_context` when the launcher is all you
    are supplying** — typically a Django context processor on a platform that
    mounts many apps, where there is a request but no single "tool".
    ``shell_context`` takes a tool name and builds a whole shell context; asking
    a context processor to invent one just to reach this validation is the wrong
    shape, and it was scitex-hub about to write that workaround that produced
    this function.

    Both functions share one implementation on purpose. Two places checking the
    same shape is how they drift, and a validator that disagrees with itself
    depending on which door you came through is worse than none.

    :param launcher: ``url`` and ``label``, both required and both non-empty.
    :raises ValueError: on a missing key, an unknown key, or a blank value.

    **Why this raises instead of returning nothing.** A missing back-link and a
    misspelled key look IDENTICAL on the rendered page — no link, no error, no
    hint. That silent-absence failure is the entire defect this feature exists
    to fix, so reproducing it in the validator would be self-defeating.

    Both key problems are reported in ONE error, deliberately. The natural typo
    is ``{"href": ..., "label": ...}``, which is simultaneously missing ``url``
    AND carrying an unknown key; reporting missing-first would send the caller
    round twice for one mistake.
    """
    missing = _LAUNCHER_KEYS - launcher.keys()
    unknown = launcher.keys() - _LAUNCHER_KEYS
    if missing or unknown:
        problems = []
        if missing:
            problems.append(f"missing {sorted(missing)}")
        if unknown:
            problems.append(f"unknown launcher key(s) {sorted(unknown)}")
        raise ValueError(
            f"launcher {' and '.join(problems)}; "
            f"expected exactly {sorted(_LAUNCHER_KEYS)}"
        )
    for key in sorted(_LAUNCHER_KEYS):
        if not str(launcher[key]).strip():
            raise ValueError(
                f"launcher[{key!r}] is empty; omit the launcher entirely to "
                "render no link, rather than passing a blank one"
            )
    return {"launcher": dict(launcher)}
