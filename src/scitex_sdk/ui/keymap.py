#!/usr/bin/env python3
"""Django integration hooks for the keymap primitive.

The keymap runtime (``ts/shell/keymap``) is framework-neutral TypeScript.
This module provides the thin Django-side surface that leaf apps import to
wire up their keymap without writing a template tag:

    from scitex_sdk.ui.keymap import render_keymap_init

    # in the app's shell template, before the keymap script:
    {{ render_keymap_init("figrecipe") }}

The rendered ``<script>`` tag carries a JSON payload of default commands and
bindings that the TS runtime reads on load. Apps can also call
``keymap_defaults()`` from their own ``AppConfig.ready()`` to register
commands in Python (for agent/MCP tooling that needs a command ID surface).
"""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "KEYMAP_GLOBAL_DEFAULTS",
    "keymap_defaults",
    "render_keymap_init",
]

#: The global keymap defaults that every scitex-sdk ui shell ships.
#: Mirrors the existing keyboard-shortcuts module's global set so the
#: transition is mechanical: same chords, same commands, new registry.
KEYMAP_GLOBAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "ai-panel:toggle": {
        "label": "Toggle AI panel",
        "group": "Global",
        "sequence": "Alt+A",
    },
    "pane:cycle-next": {
        "label": "Cycle to next pane",
        "group": "Global",
        "sequence": "Alt+T",
    },
    "pane:cycle-prev": {
        "label": "Cycle to previous pane",
        "group": "Global",
        "sequence": "Alt+Shift+T",
    },
    "pane:focus-next": {
        "label": "Focus next pane",
        "group": "Global",
        "sequence": "Alt+Right",
    },
    "pane:focus-prev": {
        "label": "Focus previous pane",
        "group": "Global",
        "sequence": "Alt+Left",
    },
    "pane:collapse-right": {
        "label": "Collapse current pane rightward",
        "group": "Global",
        "sequence": "Alt+Shift+Right",
    },
    "pane:collapse-left": {
        "label": "Collapse current pane leftward",
        "group": "Global",
        "sequence": "Alt+Shift+Left",
    },
    "file:upload": {
        "label": "Upload files",
        "group": "Global",
        "sequence": "Ctrl+U",
    },
}


def keymap_defaults() -> dict[str, dict[str, Any]]:
    """Return the global keymap defaults as a fresh dict (safe to mutate)."""
    return {k: dict(v) for k, v in KEYMAP_GLOBAL_DEFAULTS.items()}


def render_keymap_init(
    app_id: str,
    *,
    app_defaults: dict[str, dict[str, Any]] | None = None,
    mode: str | None = None,
) -> str:
    """Render a ``<script>`` tag the keymap runtime reads on load.

    Parameters
    ----------
    app_id:
        The app identifier (used for sessionStorage namespace + storage key).
    app_defaults:
        Optional per-app command overrides, same shape as
        ``KEYMAP_GLOBAL_DEFAULTS``. Merged over the global defaults.
    mode:
        Optional initial page/app mode to activate on load.

    Returns
    -------
    str
        A self-contained ``<script>`` tag. The runtime's auto-mount reads
        this tag (same pattern as ``{% scitex_js_catalog %}``).
    """
    defaults = keymap_defaults()
    if app_defaults:
        defaults.update(app_defaults)
    payload: dict[str, Any] = {
        "app": app_id,
        "defaults": defaults,
        "mode": mode,
    }
    return (
        f'<script type="application/json" '
        f'id="stx-keymap-init-{app_id}">'
        f"{json.dumps(payload, separators=(',', ':'))}"
        f"</script>"
    )


# EOF
