#!/usr/bin/env python3
"""Tell the page where it is mounted — the SERVER half of the dual-mode contract.

``static/scitex_sdk/ui/ts/_base/mount.ts`` reads a mount marker out of the document
and THROWS when none is present, because a guessed root mount works perfectly
standalone and fails only once embedded. That reader shipped in 0.12.0 with
nothing in this package emitting a marker for it to read: every scitex-ui
template emitted neither spelling, so a GUI that adopted ``mountPrefix()`` in
standalone mode got a ``MountPrefixMissingError``. A reader with no writer is
not half a feature; it is a feature that reaches nobody.

This module is the writer. :func:`mount_context` produces the context that
``_mount_marker.html`` renders, and ``standalone_shell.html`` includes that
partial in its ``<head>``.

WHAT "MOUNT PREFIX" MEANS: the part of the URL that belongs to the mount rather
than to the app. Standalone that is ``""``; as a scitex-hub built-in it is
``/apps/u/<module_name>``. Client code joins app-relative paths onto it, so it
carries no trailing slash and root is the empty string.

WHY THE VIEW MUST DECLARE ITS OWN ROUTE, and why there is deliberately NO
context processor here. ``request.path`` is the whole path — mount prefix AND
whatever route the view occupies inside the app. Subtracting the view's own
route is the only way to recover the prefix, and only the view knows that route
because the view is what wrote it in ``urls.py``. A context processor cannot
know it, so it would be silently correct for views at the app root and silently
WRONG for every other view. That is strictly worse than the throw this whole
contract is built on: a wrong prefix is indistinguishable from a right one until
a request 404s in production. So the caller passes ``view_path`` and a mismatch
raises.

Django's ``resolver_match.route`` looks like it should supply this and does not:
under ``include()`` it is the FULL concatenated pattern, so subtracting it
yields ``"/"``. scitex-app measured that directly and rejected it; recorded here
so it is not rediscovered as a clever shortcut.

``request.path``, never ``request.path_info``: ``path_info`` has ``SCRIPT_NAME``
stripped, which is exactly the prefix we are trying to read. That one is easy to
get backwards and, again, fails only when embedded.

AND NEVER ADD ``SCRIPT_NAME`` BACK ON. ``request.path`` ALREADY CONTAINS IT --
Django composes the two, at ``django/core/handlers/wsgi.py:67``::

    self.path = "%s/%s" % (script_name.rstrip("/"), path_info.replace("/", "", 1))

So ``request.META["SCRIPT_NAME"] + request.path`` does not harden anything; it
DOUBLES the prefix under precisely the convention it looks like it is guarding
against::

    SCRIPT_NAME=/apps/u/writer, PATH_INFO=/editor/
    request.path                ->  /apps/u/writer/editor/                  correct
    SCRIPT_NAME + request.path  ->  /apps/u/writer/apps/u/writer/editor/    WRONG

This is written down because it was proposed in review, in good faith, as a
change that would be "identical today and immune under both conventions". It is
identical only while ``SCRIPT_NAME`` is empty -- i.e. only in the case that never
exercises it -- so testing it standalone proves nothing and the bug ships. Two
readers reasoned their way to it independently, which is the signal that a
comment is not enough: see ``test_script_name_is_not_added_back_on`` for the
mechanical guard.

The upshot is that ``request.path`` is correct under BOTH conventions by
construction. A hub that mounts sub-apps by URL prefix and a hub that mounts them
via ``SCRIPT_NAME`` produce the same ``request.path``, so this derivation does
not depend on any dispatcher choosing not to rewrite it.

Usage in a view::

    from scitex_sdk.ui.branding import shell_context
    from scitex_sdk.ui.mount import mount_context

    def editor(request):                     # urls.py: path("editor/", editor)
        return render(request, "myapp/index.html", {
            **shell_context("Writer"),
            **mount_context(request, view_path="editor/"),
        })

An app that does not merge :func:`mount_context` gets no marker, and client code
calling ``mountPrefix()`` throws. That is the intended failure: loud, immediate,
and identical in both modes.
"""

from __future__ import annotations


#: Context key holding the prefix. Read by ``_mount_marker.html``.
MOUNT_PREFIX_KEY = "stx_mount_prefix"

#: Companion flag saying a prefix was DECLARED, as distinct from being empty.
#:
#: The template needs both because a root mount is the empty string, and
#: ``{% if stx_mount_prefix %}`` is false for it — so a single key would emit no
#: marker for the standalone case, which the reader cannot distinguish from an
#: app that never adopted the contract. "Mounted at root" and "nobody said"
#: must not render the same, and conflating them is the exact silent bug here.
#:
#: The general shape, named by scitex-dev after hitting four other instances the
#: same day (unparsed → empty set; unreadable → clean summary; ambiguous →
#: confident version; did-not-run → silence): a state the representation cannot
#: express renders as a value that looks correct, and it fails toward looking
#: FINE — so it gets consumed by downstream code rather than reported. The
#: specific trap is truthiness on a value whose falsy member is legal. Enumerate
#: the states a type cannot distinguish BEFORE choosing it.
MOUNT_DECLARED_KEY = "stx_mount_declared"

#: Name of the emitted ``<meta>``. Must match ``MOUNT_META_NAME`` in mount.ts.
MOUNT_META_NAME = "stx-mount"


class MountPrefixMismatch(ValueError):
    """``view_path`` is not a suffix of ``request.path``.

    Raised rather than falling back, for the same reason the client reader
    throws: a guessed prefix is indistinguishable from a correct one until it
    reaches production. A mismatch means the declared route and the real URL
    disagree, which is a wiring bug in the caller.
    """


def mount_prefix(request, *, view_path: str = "") -> str:
    """Return the prefix ``request`` is mounted under, without a trailing slash.

    :param request: any object with a ``path`` string (a Django ``HttpRequest``).
    :param view_path: the calling view's own route WITHIN the app, as written in
        ``urls.py``. Surrounding slashes are ignored, so ``"editor/"``,
        ``"/editor"`` and ``"editor"`` are the same. Default ``""`` is correct
        for a view mounted at the app root — which is what
        ``scitex_sdk.app.embed.scitex_urlpatterns`` emits for its editor page.
    :returns: ``""`` for a root mount, else e.g. ``"/apps/u/writer"``.
    :raises MountPrefixMismatch: if ``request`` has no string ``path``, or if
        ``view_path`` is not a trailing path segment of it.

    Root returns ``""`` so ``f"{mount_prefix(request)}/api/x"`` is well-formed
    in both modes — the same normalisation ``mount.ts`` applies client-side.
    """
    path = getattr(request, "path", None)
    if not isinstance(path, str):
        raise MountPrefixMismatch(
            f"request has no string .path (got {path!r}); the mount prefix is "
            "derived from request.path and cannot be guessed"
        )

    relative = view_path.strip().strip("/")
    head = path.rstrip("/")
    if not relative:
        return head

    tail = f"/{relative}"
    if not head.endswith(tail):
        raise MountPrefixMismatch(
            f"view_path {view_path!r} is not a trailing segment of "
            f"request.path {path!r}. Pass the route this view is registered "
            "under in urls.py, relative to the app root."
        )
    return head[: -len(tail)]


def mount_context(request, *, view_path: str = "") -> dict[str, object]:
    """Build the template context that emits the mount marker.

    Merge into any context rendered by ``standalone_shell.html`` (or by a
    template that includes ``scitex_sdk/ui/_mount_marker.html`` directly). Both keys
    are always set: see :data:`MOUNT_DECLARED_KEY` for why the flag is separate
    from the value.

    Arguments are forwarded to :func:`mount_prefix`, including its raise.
    """
    return {
        MOUNT_PREFIX_KEY: mount_prefix(request, view_path=view_path),
        MOUNT_DECLARED_KEY: True,
    }


# ============================================================================
# THE APP VERSION CONTRACT — the third attribute of the same mount container
# ============================================================================
# The states, the mount-marker contrast and the reason no fallback may exist are
# documented in the module docstring above and in the block below; this section
# lives here rather than in its own file because `data-app-version` is stamped on
# the SAME element this module's marker describes, and because src/scitex_ui sits
# at its flat-module threshold (PS-108b) — a new top-level module for one
# attribute would trade a real structural rule for a filing preference.

#: Context key a view passes into ``standalone_shell.html`` (or into any template
#: that stamps the container itself).
APP_VERSION_KEY = "app_version"

#: The DOM attribute. MUST match ``APP_VERSION_ATTRIBUTE`` in
#: ``ts/app/app-header/types.ts`` — the writer and the reader are two languages
#: apart, so a rename on either side has to fail a test, not a badge.
APP_VERSION_ATTRIBUTE = "data-app-version"


class AppVersionError(ValueError):
    """The version is not usable AS a version, and coercing it would invent one."""


def declared_app_version(app_version: str | None = None) -> str | None:
    """The version to stamp, or ``None`` when there is none — never a substitute.

    Refuses a non-string instead of ``str()``-ing it: a ``ModuleType``, a
    ``Version`` object or an object's ``repr`` all render as something that
    looks like a version, which is the same wrong-answer-that-looks-right class
    this module exists to stop. A blank or whitespace-only string is treated as
    NOT declared (state 2 above), not as a version.
    """
    if app_version is None:
        return None
    if not isinstance(app_version, str):
        raise AppVersionError(
            f"{APP_VERSION_KEY} must be a string or None, got "
            f"{type(app_version).__name__}. Refusing to coerce it: a coerced "
            "value renders as a plausible version that is not the app's."
        )
    value = app_version.strip()
    return value or None


def app_version_context(app_version: str | None = None) -> dict[str, object]:
    """Build the context key that stamps the mount container.

    Merge into any context rendered by ``standalone_shell.html``, exactly as
    :func:`scitex_sdk.ui.mount.mount_context` is merged for the mount marker.
    The key is ALWAYS set (to ``None`` when nothing was declared) so a template
    reads one key rather than testing for its presence — the value's falsiness is
    the signal, and it is safe here because no blank version is legal.
    """
    return {APP_VERSION_KEY: declared_app_version(app_version)}
