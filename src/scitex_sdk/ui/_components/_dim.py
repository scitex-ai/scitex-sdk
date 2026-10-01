#!/usr/bin/env python3
"""Dim component metadata.

The presentation half of an authorization verdict: a control that stays
visible and reachable while being unusable, carrying the reason it is
unusable and — where the verdict offers one — the route out.

Why this is a state of its own and not ``.disabled``
----------------------------------------------------
"Broken / not usable" and "available once you sign in" are different
facts. Rendering them identically tells a user that signing in will not
help, which is the login-wall behaviour the operator's ruling explicitly
rules out (2026-09-02: dimmed, visible, not hidden, not a wall).

The verdict itself is produced by ``scitex_sdk.app.authz`` and crosses the
package boundary as plain serialisable data. ``scitex-ui`` does NOT
depend on ``scitex-app``: an app depends on both, so importing the SDK
here would point that arrow backwards.

Design follows the same shape as :mod:`._tooltip` — Python registry stub
here, TS + CSS in ``static/scitex_sdk/ui/``.
"""

from .._registry import register_component


class Dim:
    name = "dim"
    version = "0.1.0"
    description = (
        "Renders an authorization verdict onto a control that stays "
        "visible: aria-disabled (never the disabled attribute, which "
        "would take the control and its explanation out of tab order), "
        "the reason via both data-tooltip and aria-describedby, and the "
        "sign-in route where the verdict carries one."
    )
    ts_entry = "scitex_sdk/ui/ts/app/dim/index"
    css_file = "scitex_sdk/ui/css/app/dim.css"
    # Pre-built pure-JS sibling for Django-template consumers that load
    # static assets directly via ``{% static %}`` with no bundler in play
    # -- the same arrangement ``combobox`` ships for scitex-todo's board.
    #
    # I first wrote this attribute out, reasoning that a server-rendered
    # consumer emits the class and ARIA attributes in its own template and
    # needs no script. ``test_ts_components_have_js_builds`` disagreed, and
    # it was right: server-rendering covers the FIRST paint, but a page
    # that re-evaluates a verdict without a reload -- after a sign-in in
    # another tab, say -- has to apply it from script, and an adopter
    # without a bundler cannot execute the .ts.
    js_file = "scitex_sdk/ui/js/app/dim.js"


register_component(Dim.name, Dim)
