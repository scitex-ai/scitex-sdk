#!/usr/bin/env python3
"""App launcher component metadata (compass L624)."""

from .._registry import register_component


class AppLauncher:
    """The standard app-launcher pattern (compass L624).

    A trigger (a grid `田` glyph + an "Apps" / "Home" label) opens a panel
    that is a GRID OF APP TILES — one tile per app the consumer supplies.
    Picking a tile emits ``stx-app-launcher:select`` (bubbles, detail
    ``{id, name}``) and the CONSUMING APP performs the navigation.

    The component owns the pattern — the markup, the BEM vocabulary, the
    grid-of-tiles layout, and the event contract. It does NOT own the app
    list (which apps exist is the app's) or the routing (the destination of a
    tile is the app's). A launcher that hardcodes destinations would couple
    every adopter to one app's route table; this keeps the destination in the
    event so the adopter stays the source of truth.

    The grid glyph (``田``) and the text label are both rendered, per the
    compass: "Add a visible Apps launcher using a grid (田) icon" + "Label it
    Apps / Home rather than relying on the logo alone". The glyph is a single
    self-contained character in the platform font — no icon font, no SVG
    asset, no bundler step — which is the whole point of a shared primitive.

    CSS: scitex_sdk/ui/css/app/app-launcher.css
    """

    name = "app-launcher"
    version = "0.1.0"
    description = (
        "Standard app-launcher pattern: grid of app tiles behind a grid-glyph "
        "trigger, emits stx-app-launcher:select"
    )
    ts_entry = "scitex_sdk/ui/ts/app/app-launcher/index"
    css_file = "scitex_sdk/ui/css/app/app-launcher.css"
    # Pre-built ES-module sibling for consumers without a bundler step: a
    # browser executes the .js module directly where it cannot execute the
    # .ts. Mirrors the TS API (same exports). Rebuild command is in the
    # file banner.
    js_file = "scitex_sdk/ui/js/app/app-launcher.js"


register_component(AppLauncher.name, AppLauncher)
