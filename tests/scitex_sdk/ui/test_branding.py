#!/usr/bin/env python3
"""Tests for the shared GUI branding convention and how the shell renders it.

The shell assertions render the real ``standalone_shell.html`` rather than
grepping it, because the defects these guard against (missing favicon,
hardcoded dark theme, unset body font) were all only visible in the rendered
page.
"""

import functools
import re
from pathlib import Path

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "DIRS": [],
            }
        ],
        DEFAULT_CHARSET="utf-8",
    )
    django.setup()

from django.template.loader import render_to_string  # noqa: E402

from scitex_sdk.ui.branding import (  # noqa: E402
    FAVICON_STATIC_PATH,
    PANE_NAMES,
    PANE_STATES,
    launcher_context,
    shell_context,
    shell_title,
)

_SHELL = "scitex_sdk/ui/standalone_shell.html"

# Accent names the shell reserves for its own state rather than for an app.
_RESERVED_ACCENTS = {"color", "tint"}


def _render(context=None):
    return render_to_string(_SHELL, context or {})


def _css(relative_path):
    from scitex_sdk.ui import get_static_dir

    return (get_static_dir() / relative_path).read_text()


def _templates_dir():
    from scitex_sdk import ui as scitex_ui

    return Path(scitex_ui.__file__).parent / "templates" / "scitex_sdk" / "ui"


def _font_tokens(css):
    """Map ``--<name>-font-family|font-size|line-height`` -> normalised value."""
    found = re.findall(r"(--(?:base|heading|mono)-font-family)\s*:\s*([^;]+);", css)
    return {name: " ".join(value.split()) for name, value in found}


def _declared_accents():
    """Accent names declared as ``--app-accent-<name>`` tokens in theme.css."""
    names = set(
        re.findall(r"--app-accent-([a-z0-9-]+)\s*:", _css("css/shell/theme.css"))
    )
    return {n for n in names if not n.endswith("-tint")} - _RESERVED_ACCENTS


def _referenced_accents():
    """Accent tokens the sidebar's mapping rows actually reference.

    Keyed on ``var(--app-accent-<name>)`` rather than on the selector name,
    because alias rows are legitimate: ``[data-app-accent="vis"]`` groups with
    ``"visualizer"`` and points at the *visualizer* token, so it neither needs
    nor has a token of its own.
    """
    names = set(
        re.findall(
            r"var\(--app-accent-([a-z0-9-]+)\)",
            _css("css/shell/stx-shell-sidebar.css"),
        )
    )
    stripped = {n[: -len("-tint")] if n.endswith("-tint") else n for n in names}
    return stripped - _RESERVED_ACCENTS


# --- title convention -------------------------------------------------------

def test_shell_title_adds_the_brand_prefix():
    # Arrange
    tool = "Writer"
    # Act
    title = shell_title(tool)
    # Assert
    assert title == "SciTeX Writer"


def test_shell_title_is_idempotent_for_an_already_branded_name():
    # Arrange
    tool = "SciTeX Writer"
    # Act
    title = shell_title(tool)
    # Assert
    assert title == "SciTeX Writer"


def test_shell_title_degrades_to_the_bare_brand_for_a_blank_name():
    # Arrange
    tool = "   "
    # Act
    title = shell_title(tool)
    # Assert
    assert title == "SciTeX"


def test_shell_context_exposes_the_branded_title_as_app_label():
    # Arrange
    tool = "Storage"
    # Act
    context = shell_context(tool)
    # Assert
    assert context["app_label"] == "SciTeX Storage"


def test_shell_context_omits_favicon_href_when_not_overridden():
    # Arrange — absent (not None), so it cannot shadow a value merged in
    # earlier and the shell falls through to the shared brand mark.
    tool = "Storage"
    # Act
    context = shell_context(tool)
    # Assert
    assert "favicon_href" not in context


def test_shell_context_keeps_an_explicit_favicon_override():
    # Arrange
    own = "/static/own.svg"
    # Act
    context = shell_context("Storage", favicon_href=own)
    # Assert
    assert context["favicon_href"] == own


# --- favicon ----------------------------------------------------------------

def test_shell_falls_back_to_the_shared_brand_favicon():
    # Arrange
    context = {"app_label": "SciTeX Storage"}
    # Act
    html = _render(context)
    # Assert
    assert FAVICON_STATIC_PATH in html


def test_shell_uses_favicon_href_when_the_app_overrides_it():
    # Arrange
    context = {"favicon_href": "/static/own.svg"}
    # Act
    html = _render(context)
    # Assert
    assert 'href="/static/own.svg"' in html


def test_shared_favicon_asset_is_shipped_in_the_package():
    # Arrange — get_static_dir() is the staticfiles root's scitex_sdk/ui/ dir, so
    # the namespaced FAVICON_STATIC_PATH is relative to its parent.
    from scitex_sdk.ui import get_static_dir

    # Act
    asset = get_static_dir().parents[1] / FAVICON_STATIC_PATH
    # Assert
    assert asset.is_file()


# --- shell-free branding partial --------------------------------------------

def test_branding_partial_renders_the_brand_favicon_without_the_shell():
    # Arrange — scholar and hub own their own layout and never render the shell,
    # so branding must be reachable without adopting the workspace.
    context = {}
    # Act
    html = render_to_string("scitex_sdk/ui/_branding_head.html", context)
    # Assert
    assert FAVICON_STATIC_PATH in html


def test_branding_partial_honours_an_explicit_favicon_override():
    # Arrange
    context = {"favicon_href": "/static/own.svg"}
    # Act
    html = render_to_string("scitex_sdk/ui/_branding_head.html", context)
    # Assert
    assert 'href="/static/own.svg"' in html


def test_branding_partial_emits_no_layout_markup():
    # Arrange — a consumer pastes this into its OWN <head>; anything structural
    # would fight the layout it already has.
    context = {}
    # Act
    html = render_to_string("scitex_sdk/ui/_branding_head.html", context).strip()
    # Assert
    assert html.startswith("<link") and html.endswith("/>")


def test_shell_reuses_the_branding_partial_rather_than_duplicating_it():
    # Arrange — one source for what SciTeX tab branding is.
    shell = (
        _templates_dir() / "standalone_shell.html"
    ).read_text()
    # Act
    includes_partial = '{% include "scitex_sdk/ui/_branding_head.html" %}' in shell
    # Assert
    assert includes_partial


# --- theme ------------------------------------------------------------------

def test_shell_does_not_hardcode_a_resolved_theme():
    # Arrange — regression: <html data-theme="dark"> overrode a stored light
    # preference on every standalone GUI.
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert 'data-theme="dark"' not in html


def test_shell_defaults_the_theme_to_dark_for_the_boot_script():
    # Arrange
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert 'data-theme-default="dark"' in html


def test_shell_honours_an_explicit_light_theme_default():
    # Arrange
    context = shell_context("Storage", theme_default="light")
    # Act
    html = _render(context)
    # Assert
    assert 'data-theme-default="light"' in html


def test_shell_inlines_the_theme_boot_rather_than_fetching_it():
    # Arrange — an external or deferred script paints the wrong theme first, and
    # costs a render-blocking request on every page (scitex-cards, 2026-07-18).
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert 'localStorage.getItem("stx-theme")' in html


def test_shell_head_makes_no_blocking_request_for_the_theme_boot():
    # Arrange
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert "theme-boot.js" not in html


def test_shell_head_makes_no_blocking_request_for_typography_tokens():
    # Arrange — the font tokens moved into theme.css, which the shell already
    # loads, so this stylesheet is no longer fetched separately.
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert "primitives/typography-vars.css" not in html


# --- typography -------------------------------------------------------------

def test_shell_theme_css_defines_the_base_font_family():
    # Arrange — without this token the UA default wins and body text renders in
    # Times New Roman on every standalone GUI.
    theme = _css("css/shell/theme.css")
    # Act
    declares_font = "--base-font-family:" in theme
    # Assert
    assert declares_font


def test_shell_font_tokens_match_the_primitives_layer():
    # Arrange — theme.css duplicates the primitives font tokens to avoid a second
    # blocking stylesheet. That copy must not drift, so compare the values.
    shell = _font_tokens(_css("css/shell/theme.css"))
    # Act
    primitives = _font_tokens(_css("css/primitives/typography-vars.css"))
    # Assert
    assert shell == {k: primitives[k] for k in shell}


# --- mobile layout ----------------------------------------------------------

def test_shell_links_the_mobile_stylesheet():
    # Arrange — regression: the shell linked every desktop layout stylesheet
    # but never mobile.css, whose @media (max-width: 768px) rules are the only
    # thing that collapses the fixed-width side panes. Without it the
    # overflow-hidden flex row pushed .ws-module-pane off-screen, so every
    # standalone GUI rendered completely blank on phones (scitex.ai
    # /apps/storage/, 2026-07-22).
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert "scitex_sdk/ui/css/shell/mobile.css" in html


def test_mobile_stylesheet_is_shipped_in_the_package():
    # Arrange — a linked-but-unshipped stylesheet would 404 and reproduce the
    # same blank page; the favicon shipped exactly that way in 0.7.0.
    from scitex_sdk.ui import get_static_dir

    # Act
    asset = get_static_dir() / "css/shell/mobile.css"
    # Assert
    assert asset.is_file()


def test_mobile_stylesheet_scopes_its_rules_to_small_viewports():
    # Arrange — the shell now loads mobile.css unconditionally, so its rules
    # must stay inside a small-viewport media query or they would restyle
    # desktop layouts too.
    css = _css("css/shell/mobile.css")
    # Act
    scoped = "@media (max-width: 768px)" in css
    # Assert
    assert scoped


# --- accent -----------------------------------------------------------------

def test_shell_sets_the_app_accent_when_one_is_given():
    # Arrange
    context = shell_context("Storage", accent="storage")
    # Act
    html = _render(context)
    # Assert
    assert 'data-app-accent="storage"' in html


def test_shell_omits_the_app_accent_attribute_when_none_is_given():
    # Arrange
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert "data-app-accent" not in html


def test_every_accent_token_is_referenced_by_a_mapping_row():
    # Arrange — a token no row references is dead: apps set the attribute and
    # nothing lights up. `notebook` sat in that state until 0.7.0.
    declared = _declared_accents()
    # Act
    unreferenced = declared - _referenced_accents()
    # Assert
    assert unreferenced == set()


def test_every_referenced_accent_token_is_declared():
    # Arrange — the mirror failure: a row pointing at a var that was never
    # declared resolves to nothing, so the accent line silently disappears.
    referenced = _referenced_accents()
    # Act
    undeclared = referenced - _declared_accents()
    # Assert
    assert undeclared == set()


# --- declared pane contract -------------------------------------------------

def test_shell_hides_a_pane_declared_unused():
    # Arrange
    context = shell_context("Storage", panes={"ai": "unused"})
    # Act
    html = _render(context)
    # Assert
    assert 'class="ws-ai-pane ws-pane-unused"' in html


def test_shell_keeps_a_pane_declared_client_populated():
    # Arrange — THE regression this design exists for. scitex-writer's file tree
    # has zero server-rendered children (they do not override worktree_preseed)
    # and fills from data-working-dir after mount, so an emptiness check would
    # have collapsed their primary working surface on every page load.
    context = shell_context("Writer", panes={"files": "client-populated"})
    # Act
    html = _render(context)
    # Assert
    assert "ws-pane-unused" not in html


def test_shell_keeps_every_pane_when_nothing_is_declared():
    # Arrange — opt-in: forgetting to declare leaves the page as it is today,
    # which is the whole reason this is not opt-out.
    context = shell_context("Writer")
    # Act
    html = _render(context)
    # Assert
    assert "ws-pane-unused" not in html


def test_shell_hides_only_the_panes_declared_unused():
    # Arrange
    context = shell_context("Storage", panes={"ai": "unused", "files": "used"})
    # Act
    html = _render(context)
    # Assert
    assert html.count("ws-pane-unused") == 1


def test_shell_context_rejects_an_unknown_pane_name():
    # Arrange — a typo must fail loudly; silently leaving the pane visible is
    # indistinguishable from never having declared it.
    panes = {"files_tree": "unused"}
    # Act
    declare = functools.partial(shell_context, "Storage", panes=panes)
    # Assert
    with pytest.raises(ValueError, match="unknown pane"):
        declare()


def test_shell_context_rejects_an_unknown_pane_state():
    # Arrange
    panes = {"files": "hidden"}
    # Act
    declare = functools.partial(shell_context, "Storage", panes=panes)
    # Assert
    with pytest.raises(ValueError, match="unknown state"):
        declare()


@pytest.mark.parametrize("pane", PANE_NAMES)
def test_every_declared_pane_name_actually_collapses(pane):
    # Arrange — PANE_NAMES is the contract's vocabulary and the validator
    # accepts every member of it, but nothing yet made the SHELL honour one.
    # A name added to the tuple would validate, render no change, and leave the
    # app's declaration silently ignored — which is the exact failure the
    # unknown-name ValueError exists to prevent, one level up: an accepted
    # declaration that does nothing looks identical to never having declared.
    # Parametrising over the constant is what makes a future fourth pane fail
    # HERE rather than in a consumer's layout. Until this test, `viewer` was a
    # legal name with no assertion that it did anything.
    context = shell_context("Storage", panes={pane: "unused"})
    # Act
    html = _render(context)
    # Assert
    assert html.count("ws-pane-unused") == 1


def test_the_shell_honours_exactly_the_declared_pane_names():
    # Arrange — the other direction: a template condition on a pane no app can
    # declare is dead code, and a rename of the constant that missed the
    # template would leave the old name honoured and the new one inert.
    template = (_templates_dir() / "standalone_shell.html").read_text()
    # Act
    honoured = set(re.findall(r"panes\.(\w+)\s*==\s*'unused'", template))
    # Assert — no separate positive control is needed here, and adding one
    # would be cargo cult. This guard cannot pass vacuously: the right-hand
    # side is a non-empty literal constant, so a regex that goes stale (a
    # template reformat, a switch to double quotes) yields the empty set and
    # FAILS the comparison. A control is only load-bearing when BOTH sides are
    # extracted and can go empty together.
    assert honoured == set(PANE_NAMES)


@pytest.mark.parametrize("state", PANE_STATES)
def test_only_the_unused_pane_state_changes_the_layout(state):
    # Arrange — PANE_STATES documents that "client-populated" and "used" are
    # equivalent today and both mean leave it alone. That is prose in a
    # docstring until something asserts it, and the two non-collapsing states
    # are the ones a consumer relies on to NOT lose their pane.
    context = shell_context("Storage", panes={"ai": state})
    # Act
    html = _render(context)
    # Assert
    assert html.count("ws-pane-unused") == (1 if state == "unused" else 0)


def test_shell_context_omits_panes_when_none_are_declared():
    # Arrange
    tool = "Storage"
    # Act
    context = shell_context(tool)
    # Assert
    assert "panes" not in context


def test_shell_context_omits_launcher_when_none_is_declared():
    # Arrange — a STANDALONE app supplies no destination, and must get no link.
    # Per the dual-mode contract it is itself mounted at "/", so an invented
    # link would point at the page it is on.
    tool = "Storage"
    # Act
    context = shell_context(tool)
    # Assert
    assert "launcher" not in context


def test_shell_context_carries_a_declared_launcher():
    # Arrange
    launcher = {"url": "/apps/store/", "label": "Apps"}
    # Act
    context = shell_context("Storage", launcher=launcher)
    # Assert
    assert context["launcher"] == launcher


def test_shell_context_rejects_a_launcher_missing_a_key():
    # Arrange — a half-specified launcher renders a link with no label or no
    # destination, which looks the same as the defect this feature fixes.
    launcher = {"url": "/apps/store/"}
    # Act
    declare = functools.partial(shell_context, "Storage", launcher=launcher)
    # Assert
    with pytest.raises(ValueError, match="missing"):
        declare()


def test_shell_context_rejects_an_unknown_launcher_key():
    # Arrange — `href` is the natural wrong guess, and silently ignoring it
    # would render nothing while the caller believes they supplied a link.
    launcher = {"href": "/apps/store/", "label": "Apps"}
    # Act
    declare = functools.partial(shell_context, "Storage", launcher=launcher)
    # Assert
    with pytest.raises(ValueError, match="unknown launcher key"):
        declare()


def test_shell_context_rejects_an_empty_launcher_value():
    # Arrange — a blank url is worse than no launcher: it renders a link that
    # goes nowhere, so the page LOOKS escapable and is not.
    launcher = {"url": "   ", "label": "Apps"}
    # Act
    declare = functools.partial(shell_context, "Storage", launcher=launcher)
    # Assert
    with pytest.raises(ValueError, match="empty"):
        declare()


def test_launcher_context_returns_a_template_ready_dict():
    # Arrange — the shape a context processor returns directly.
    launcher = {"url": "/apps/store/", "label": "Apps"}
    # Act
    context = launcher_context(launcher)
    # Assert
    assert context == {"launcher": launcher}


def test_launcher_context_rejects_the_same_shapes_shell_context_does():
    # Arrange — ONE implementation backs both entry points, so a caller cannot
    # get a laxer check by coming through the other door. This asserts they
    # agree rather than trusting that they do.
    bad = {"href": "/apps/store/", "label": "Apps"}
    # Act
    via_helper = functools.partial(launcher_context, bad)
    # Assert
    with pytest.raises(ValueError, match="unknown launcher key"):
        via_helper()


def test_shell_context_and_launcher_context_agree_on_a_good_value():
    # Arrange
    launcher = {"url": "/apps/store/", "label": "Apps"}
    # Act
    from_shell = shell_context("Storage", launcher=launcher)["launcher"]
    # Assert
    assert from_shell == launcher_context(launcher)["launcher"]
