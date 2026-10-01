#!/usr/bin/env python3
"""App Help component metadata."""

from .._registry import register_component


class AppHelp:
    """In-app "How to use": a `?` help panel + first-open coach-mark tour.

    One per-app steps file (JSON/YAML, EN/JA) feeds both surfaces. A leaf
    declares its steps and calls ``{% stx_help "<app>" steps_json="..." %}``
    — the tag renders the `?` button and the guide payload, the prebuilt
    module auto-mounts every ``[data-stx-help]`` root and exposes
    ``window.stxHelp.open()/close()/replay()``. Steps with a ``target``
    selector are tour stops; steps without one are plain panel content.
    The first-open tour runs once per app (``stx-help:<app>:done`` in
    localStorage) and can be replayed from the panel footer.

    CSS: scitex_sdk/ui/css/app/app-help.css
    """

    name = "app-help"
    version = "0.1.0"
    description = (
        "In-app How-to-use guide: `?` help panel + first-open coach-mark tour "
        "from one per-app EN/JA steps file (stxHelp.open/close/replay)"
    )
    ts_entry = "scitex_sdk/ui/ts/app/app-help/index"
    css_file = "scitex_sdk/ui/css/app/app-help.css"
    # Pre-built module for pages without a bundler; also sets window.stxHelp and auto-mounts.
    js_file = "scitex_sdk/ui/js/app/app-help.js"


register_component(AppHelp.name, AppHelp)
