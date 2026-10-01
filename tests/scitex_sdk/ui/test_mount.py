#!/usr/bin/env python3
"""The server half of the dual-mode contract: emit the mount prefix.

``ts/_base/mount.ts`` reads a mount marker and throws when there is none. That
reader shipped with nothing in this package emitting a marker, so a GUI adopting
``mountPrefix()`` in standalone mode got a ``MountPrefixMissingError``. These
tests pin the writer: the derivation, and — the part that actually failed last
time — that the marker reaches the rendered ``standalone_shell.html``.
"""

import io

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui"],
        DEFAULT_CHARSET="utf-8",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
    )
    django.setup()

from django.template.loader import render_to_string  # noqa: E402

from scitex_sdk.ui.mount import (  # noqa: E402
    APP_VERSION_ATTRIBUTE,
    APP_VERSION_KEY,
    AppVersionError,
    app_version_context,
    declared_app_version,
    MOUNT_DECLARED_KEY,
    MOUNT_META_NAME,
    MOUNT_PREFIX_KEY,
    MountPrefixMismatch,
    mount_context,
    mount_prefix,
)

from scitex_sdk import ui as scitex_ui  # noqa: E402

from tests._checkout import static_dir, templates_dir  # noqa: E402

_MARKER = "scitex_sdk/ui/_mount_marker.html"
_SHELL = "scitex_sdk/ui/standalone_shell.html"


class _Req:
    """Minimal stand-in: mount_prefix only ever reads ``.path``."""

    def __init__(self, path):
        self.path = path


def _outcome(request, **kwargs):
    """Return the prefix, or the raised error, so Act stays one statement.

    Keeps each test to a single assertion without hiding which of the two
    happened — an ``except: pass`` here would turn "it raised" and "it returned
    the wrong thing" into the same green.
    """
    try:
        return mount_prefix(request, **kwargs)
    except MountPrefixMismatch as exc:
        return exc


# ─────────────────────────────── derivation ────────────────────────────────


def test_root_mount_is_the_empty_string_not_a_slash() -> None:
    # Arrange — "" is what makes f"{prefix}/api/x" well-formed in both modes,
    # matching normalise() in mount.ts. A "/" here would double the slash.
    request = _Req("/")
    # Act
    prefix = mount_prefix(request)
    # Assert
    assert prefix == ""


def test_embedded_mount_returns_the_hub_prefix_without_a_trailing_slash() -> None:
    # Arrange — the real scitex-hub shape for a published app.
    request = _Req("/apps/u/writer/")
    # Act
    prefix = mount_prefix(request)
    # Assert
    assert prefix == "/apps/u/writer"


def test_the_views_own_route_is_subtracted() -> None:
    # Arrange — request.path carries mount prefix AND the view's own route.
    # Only the view knows the latter, so it declares it; see mount.py for why
    # a context processor cannot do this.
    request = _Req("/apps/u/writer/editor/")
    # Act
    prefix = mount_prefix(request, view_path="editor/")
    # Assert
    assert prefix == "/apps/u/writer"


def _wsgi_request(script_name: str, path_info: str):
    """A REAL ``WSGIRequest``, so Django composes ``.path`` rather than a stub.

    The whole point of the two tests below is that ``request.path`` already
    contains ``SCRIPT_NAME``. ``_Req`` cannot show that — it takes ``.path`` as
    given, which is exactly the assumption under test. Only Django's own
    composition (``core/handlers/wsgi.py:67``) can prove it.
    """
    from django.core.handlers.wsgi import WSGIRequest

    return WSGIRequest(
        {
            "REQUEST_METHOD": "GET",
            "SCRIPT_NAME": script_name,
            "PATH_INFO": path_info,
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "wsgi.input": io.BytesIO(b""),
        }
    )


def test_django_composes_path_from_script_name_and_path_info() -> None:
    # Arrange — the positive control for the guard below. If this ever fails,
    # Django changed its composition and the guard's premise is gone; without
    # it, a green guard would prove nothing.
    request = _wsgi_request("/apps/u/writer", "/editor/")
    # Act
    path = request.path
    # Assert
    assert path == "/apps/u/writer/editor/"


def test_script_name_is_not_added_back_on() -> None:
    # Arrange — a SCRIPT_NAME-mounted sub-app, the convention this derivation
    # must survive. Proposed in review as `META["SCRIPT_NAME"] + request.path`,
    # which looks convention-immune and is identical ONLY while SCRIPT_NAME is
    # empty — i.e. only in the standalone case that never exercises it. That
    # form yields "/apps/u/writer/apps/u/writer", so this test is what turns
    # the docstring warning into something that bites. See mount.py.
    request = _wsgi_request("/apps/u/writer", "/editor/")
    # Act
    prefix = mount_prefix(request, view_path="editor/")
    # Assert
    assert prefix == "/apps/u/writer"


def test_script_name_mounted_root_view_still_yields_the_mount() -> None:
    # Arrange — same convention, view at the app root, so view_path is "".
    # Doubling would be invisible here without this case: the mismatch raise
    # never fires when there is no route to subtract.
    request = _wsgi_request("/apps/u/writer", "/")
    # Act
    prefix = mount_prefix(request, view_path="")
    # Assert
    assert prefix == "/apps/u/writer"


@pytest.mark.parametrize("declared", ["editor", "/editor", "editor/", " editor/ "])
def test_view_path_slashes_and_spacing_do_not_change_the_answer(declared) -> None:
    # Arrange — urls.py spellings vary ("editor/" vs "editor"); a caller must
    # not have to guess which form this helper wants.
    request = _Req("/apps/u/writer/editor/")
    # Act
    prefix = mount_prefix(request, view_path=declared)
    # Assert
    assert prefix == "/apps/u/writer"


def test_subtraction_matches_whole_segments_only() -> None:
    # Arrange — "/my-editor" ENDS WITH the text "editor". Subtracting on raw
    # text would return "/my-" and produce a URL that resolves nowhere; the
    # leading slash in the compared tail is what prevents it.
    request = _Req("/my-editor/")
    # Act
    outcome = _outcome(request, view_path="editor")
    # Assert
    assert isinstance(outcome, MountPrefixMismatch)


def test_a_view_path_that_is_not_in_the_url_raises_rather_than_guessing() -> None:
    # Arrange — declared route and real URL disagree: a wiring bug. Falling
    # back would hand out a prefix that is wrong in exactly the way this whole
    # contract exists to make impossible.
    request = _Req("/apps/u/writer/")
    # Act
    outcome = _outcome(request, view_path="editor")
    # Assert
    assert isinstance(outcome, MountPrefixMismatch)


def test_the_mismatch_message_names_the_declared_route() -> None:
    # Arrange — an error that does not say what disagreed leaves the reader
    # grepping.
    request = _Req("/apps/u/writer/")
    # Act
    message = str(_outcome(request, view_path="editor"))
    # Assert
    assert "editor" in message


def test_the_mismatch_message_names_the_actual_path() -> None:
    # Arrange — the other half of the same sentence: which URL was seen.
    request = _Req("/apps/u/writer/")
    # Act
    message = str(_outcome(request, view_path="editor"))
    # Assert
    assert "/apps/u/writer/" in message


def test_a_request_without_a_path_raises() -> None:
    # Arrange — something that is not a request at all. Returning "" here
    # would look exactly like a legitimate root mount.
    request = object()
    # Act
    outcome = _outcome(request)
    # Assert
    assert isinstance(outcome, MountPrefixMismatch)


# ──────────────────────────────── context ──────────────────────────────────


def test_context_carries_the_prefix_and_the_declared_flag() -> None:
    # Arrange
    request = _Req("/apps/u/writer/")
    # Act
    context = mount_context(request)
    # Assert
    assert context == {MOUNT_PREFIX_KEY: "/apps/u/writer", MOUNT_DECLARED_KEY: True}


def test_the_declared_flag_is_true_even_at_root_where_the_prefix_is_empty() -> None:
    # Arrange — the reason the flag exists at all. `{% if stx_mount_prefix %}`
    # is FALSE for a root mount, so a single key would emit no marker
    # standalone, which the reader treats as an integration bug.
    request = _Req("/")
    # Act
    context = mount_context(request)
    # Assert
    assert context == {MOUNT_PREFIX_KEY: "", MOUNT_DECLARED_KEY: True}


# ───────────────────────── the partial, rendered ───────────────────────────


def test_the_partial_emits_the_meta_for_an_embedded_mount() -> None:
    # Arrange
    context = mount_context(_Req("/apps/u/writer/"))
    # Act
    html = render_to_string(_MARKER, context)
    # Assert
    assert f'<meta name="{MOUNT_META_NAME}" content="/apps/u/writer" />' in html


def test_the_partial_still_emits_the_meta_at_root_with_empty_content() -> None:
    # Arrange — the case a value-only template check would silently drop.
    context = mount_context(_Req("/"))
    # Act
    html = render_to_string(_MARKER, context)
    # Assert
    assert f'<meta name="{MOUNT_META_NAME}" content="" />' in html


def test_the_partial_emits_nothing_when_no_prefix_was_declared() -> None:
    # Arrange — an app that never merged mount_context. It must get NO marker,
    # so the client reader throws. Emitting content="" here would be the
    # guessed root mount, arriving from the server instead of the browser.
    context = {}
    # Act
    html = render_to_string(_MARKER, context)
    # Assert
    assert MOUNT_META_NAME not in html


def test_the_partial_ignores_a_bare_prefix_without_the_flag() -> None:
    # Arrange — a caller who set the value by hand instead of using
    # mount_context. Half the contract is not the contract; the flag is what
    # asserts a server actually derived this.
    context = {MOUNT_PREFIX_KEY: "/apps/u/writer"}
    # Act
    html = render_to_string(_MARKER, context)
    # Assert
    assert MOUNT_META_NAME not in html


# ──────────────────── the shell, rendered — the reach test ─────────────────


def test_the_shell_emits_the_marker_when_the_view_declares_it() -> None:
    # Arrange — THE test this feature was missing. mount.ts shipped correct and
    # unreachable because no template fed it; asserting on the partial alone
    # would have passed then too.
    context = mount_context(_Req("/apps/u/writer/"))
    # Act
    html = render_to_string(_SHELL, context)
    # Assert
    assert f'<meta name="{MOUNT_META_NAME}" content="/apps/u/writer" />' in html


def test_the_shell_emits_the_marker_at_root_too() -> None:
    # Arrange — standalone is the mode where a missing marker is invisible,
    # because hardcoded "/" happens to work there.
    context = mount_context(_Req("/"))
    # Act
    html = render_to_string(_SHELL, context)
    # Assert
    assert f'<meta name="{MOUNT_META_NAME}" content="" />' in html


def test_the_shell_emits_no_marker_for_an_app_that_has_not_adopted() -> None:
    # Arrange — every GUI extending the shell today. They must be unchanged by
    # this release: no marker, and their existing code path untouched.
    context = {}
    # Act
    html = render_to_string(_SHELL, context)
    # Assert
    assert MOUNT_META_NAME not in html


def test_the_marker_lands_in_the_head_not_the_body() -> None:
    # Arrange — mount.ts queries the document for meta[name], which would find
    # it anywhere; but a <meta> in <body> is invalid HTML and browsers relocate
    # it. Assert placement rather than trusting the query to be forgiving.
    html = render_to_string(_SHELL, mount_context(_Req("/apps/u/writer/")))
    # Act
    marker_at = html.index(f'name="{MOUNT_META_NAME}"')
    # Assert
    assert marker_at < html.index("</head>")



#: The app-header primitive's reader (PR #250) — a cross-language contract, so
#: the writer here and the reader there are asserted to agree on the name.
_READER = static_dir() / "ts" / "app" / "app-header" / "types.ts"


def _mount_tag(html: str) -> str:
    """The <div id="root"> open tag — where data-app-version must land."""
    start = html.find('id="root"')
    if start == -1:
        return ""
    return html[max(0, start - 200): html.find(">", start) + 1]

# ═══════════════════════════════════════════════════════════════════════════
# THE APP VERSION CONTRACT — stamped when declared, NEVER invented
# ═══════════════════════════════════════════════════════════════════════════
# Coordinator direction 2026-09-17: the standalone/mount shell takes an explicit
# ``app_version`` input and stamps ``data-app-version`` on the app mount
# container, fail-closed, with no hardcoded fallback — the half that unblocks
# FigRecipe and every leaf version badge.
#
# WHY IT IS HERE: the contract lives in this module (mount.py), so its tests
# mirror it (PS-204), and these arms are the render-equivalent half — the shell
# is rendered through Django's own engine and the emitted DOM is read back,
# because the defect being guarded only appears once a template RUNS ("mount.ts
# shipped correct and unreachable because no template fed it", one layer up).
#
# One assertion per test, three marker lines (PA-307 §3).
# ── The pure half ──────────────────────────────────────────────────────────


def test_a_declared_version_is_returned_trimmed() -> None:
    # Arrange
    raw = "  1.4.0  "
    # Act
    value = declared_app_version(raw)
    # Assert
    assert value == "1.4.0"


def test_already_clean_version_is_returned_unchanged() -> None:
    # Arrange
    raw = "1.4.0"
    # Act
    value = declared_app_version(raw)
    # Assert
    assert value == "1.4.0"


def test_no_version_declared_is_none_not_a_default() -> None:
    # Arrange — nothing was passed in at all (state 3).
    nothing = None
    # Act
    value = declared_app_version(nothing)
    # Assert
    assert value is None


def test_a_blank_version_is_treated_as_not_declared() -> None:
    # Arrange — state 2: declared unknown. A blank string is NOT a version.
    # Act
    value = declared_app_version("   ")
    # Assert
    assert value is None


def test_a_non_string_version_is_refused_rather_than_coerced() -> None:
    # Arrange — a ModuleType or a Version object str()s into something that
    # LOOKS like a version, which is the wrong-answer-that-looks-right class.
    not_a_string = scitex_ui
    # Act
    # Assert — the refusal IS the assertion, and it must be loud.
    with pytest.raises(AppVersionError, match="must be a string or None"):
        declared_app_version(not_a_string)  # type: ignore[arg-type]


def test_the_context_key_is_always_present() -> None:
    # Arrange — one key, always set: the value's falsiness is the signal, which
    # is safe here because NO blank version is legal (contrast the mount prefix).
    # Act
    context = app_version_context()
    # Assert
    assert context[APP_VERSION_KEY] is None and APP_VERSION_KEY in context


# ── The rendered shell: the mount container read back ──────────────────────


def test_a_declared_version_is_stamped_on_the_mount_container() -> None:
    # Arrange
    context = app_version_context("1.4.0")
    # Act
    html = render_to_string(_SHELL, context)
    # Assert
    assert f'{APP_VERSION_ATTRIBUTE}="1.4.0"' in _mount_tag(html)


def test_the_attribute_lands_within_the_mount_container_tag() -> None:
    # Arrange — the reader resolves from the mount ROOT first, so an attribute
    # anywhere else on the page (an ancestor's meta, the body) would still work
    # by luck and hide a regression here.
    context = app_version_context("2.0.1")
    # Act
    tag = _mount_tag(render_to_string(_SHELL, context))
    # Assert
    assert APP_VERSION_ATTRIBUTE in tag and 'id="root"' in tag


def test_an_undeclared_version_stamps_no_attribute_at_all() -> None:
    # Arrange — state 3: every GUI extending the shell today. They must be
    # unchanged by this release: no attribute, no marker, nothing new.
    # The assertion is on a STAMPED attribute (name="value"), not on the bare
    # name: the template's own comment names the attribute in prose, and a
    # check that cannot tell prose from markup is the false-positive shape this
    # repo keeps carding.
    # Act
    html = render_to_string(_SHELL, {})
    # Assert
    assert f'{APP_VERSION_ATTRIBUTE}="' not in html


def test_a_blank_version_stamps_no_attribute_either() -> None:
    # Arrange — state 2 must render exactly like state 3: the badge is absent
    # rather than empty, because an empty attribute reads as a declared value.
    # Act
    html = render_to_string(_SHELL, app_version_context("   "))
    # Assert
    assert f'{APP_VERSION_ATTRIBUTE}="' not in html


def test_the_shell_never_falls_back_to_its_own_version() -> None:
    # Arrange — THE defect this contract exists to prevent: a leaf's badge
    # showing scitex-ui's number because the shell substituted its own.
    # Act
    html = render_to_string(_SHELL, {})
    # Assert
    assert scitex_ui.__version__ not in html


def test_the_template_declares_no_default_for_the_version() -> None:
    # Arrange — `{{ app_version|default:... }}` is the fallback, one filter away.
    template = (
        templates_dir() / "scitex_sdk" / "ui" / "standalone_shell.html"
    ).read_text()
    # Act
    filtered = "app_version|default" in template
    # Assert
    assert filtered is False


# ── Writer/reader agreement across the language boundary ───────────────────


def test_the_writer_constant_is_a_non_empty_attribute_name() -> None:
    # Arrange — pin the writer even while the reader is unmerged, so "the test
    # skipped" can never be the only thing said about this half of the contract.
    # Act
    named = APP_VERSION_ATTRIBUTE.startswith("data-") and len(APP_VERSION_ATTRIBUTE) > 10
    # Assert
    assert named


@pytest.mark.skipif(
    not _READER.is_file(),
    reason=(
        "ts/app/app-header/types.ts is not in this tree yet — it lands with the "
        "app-header primitive (PR #250). The writer half is asserted above."
    ),
)
def test_the_stamped_attribute_matches_the_reader_constant() -> None:
    # Arrange — the writer is Python, the reader is TypeScript
    # (ts/app/app-header/types.ts, PR #250): a rename on either side must fail
    # HERE rather than leave a badge that never renders. Skipped with a named
    # reason only while that file is absent, so the arm activates on merge
    # instead of silently passing.
    import re

    match = re.search(r'APP_VERSION_ATTRIBUTE\s*=\s*"([^"]+)"', _READER.read_text())
    # Act
    reader_name = match.group(1) if match else None
    # Assert
    assert reader_name == APP_VERSION_ATTRIBUTE
