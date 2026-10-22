#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scitex-sdk's declared agent guardrails (federation leaf).

Registered under the ``scitex_dev.hooks`` entry-point group in
pyproject.toml exactly like any downstream package's provider; scitex-dev
aggregates them via ``discover_hooks()`` with no special-casing.

SCOPE. Guardrails about the SDK's own surfaces and contracts — theme
tokens, the component corpus, the mount contract. Guardrails about dev
workflow belong to scitex-dev; about containers to
scitex-agent-container. Each declares its own.
"""

from __future__ import annotations

try:
    from scitex_dev.hooks import HookRule
except ImportError:  # scitex-dev absent: standalone SDK use needs no hooks
    HookRule = None  # type: ignore[assignment,misc]


def provide() -> list:
    """Return scitex-sdk's declared guardrails."""
    if HookRule is None:
        return []
    return [
        HookRule(
            id="sdk.no-unthemed-scrollbar",
            rule="Do not ship scrollbar colours outside the shared "
            "shell/scrollbars.css surface — no raw scrollbar-color / "
            "::-webkit-scrollbar thumb/track colours in leaf CSS, and "
            "no unstyled scroll container that renders OS-default "
            "scrollbars on a themed page.",
            reason="Measured 2026-10-22 (operator): the FigRecipe canvas "
            "shipped a light native scrollbar on the dark theme because "
            "scrollbars were the one chrome surface with no shared home "
            "(UI-105 only banned raw hex, it never provided the tokens). "
            "Per-leaf literals fork by theme; the shared surface tracks "
            "light/dark via workspace tokens.",
            event="pre-tool-use",
            severity="warn",
            matches=("Edit", "Write"),
            provider="scitex-sdk",
            check="scitex_sdk.ui._linter._checker:scan_path",
            doctrine="src/scitex_sdk/ui/_skills/scitex-ui/40_component-usage-doctrine.md",
        ),
    ]


__all__ = ["provide"]
