"""Linter plugin for scitex-ui: UI-101..105 component-usage rules.

Registered via entry point `scitex_dev.linter.plugins` so the rules
appear in `scitex-linter list-rules` once both `scitex-ui` and
`scitex-dev` are installed.

The `checkers` slot is intentionally empty — scitex-dev's in-tree
checker dispatch is Python-AST-only (each `checker_cls(lines,
config).visit(tree)` is called against the .py AST), and the rules
below target CSS / HTML / TSX file surfaces. Active scanning of those
files is provided by the standalone walker in
:mod:`scitex_sdk.ui._linter._checker`, invoked via the `scitex-sdk ui lint`
CLI subcommand (see :mod:`scitex_sdk.ui._linter._cli`). The two paths are
complementary: registration here makes the rule corpus discoverable
via the canonical entry-point; enforcement happens via the CLI walker
that knows how to read non-Python files.

Doctrine: `src/scitex_sdk/ui/_skills/scitex-ui/40_component-usage-doctrine.md`.
"""

from __future__ import annotations

from ._linter._rules import build_rules


def get_plugin() -> dict:
    """Return scitex-sdk ui linter rules.

    Returns
    -------
    dict
        ``{"rules": [...], "call_rules": {}, "axes_hints": {}, "checkers": []}``
        following the
        ``scitex_dev.linter._plugin_loader.load_plugins`` contract.
    """
    return {
        "rules": list(build_rules().values()),
        "call_rules": {},
        "axes_hints": {},
        "checkers": [],
    }


__all__ = ["get_plugin"]
