"""SDK-owned UI-101..107 component-usage linter rules.

Registered via entry point `scitex_dev.linter.plugins` so the rules
appear in `scitex-linter list-rules` once both `scitex-sdk` and a compatible
`scitex-dev` are installed. The SDK declares the exact predecessor provider
whose seven rules it replaces; installing the old UI distribution alongside
the SDK therefore keeps one canonical rule corpus.

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
        The four historical payload keys remain available, with an additive
        ``replaces`` tuple following ``scitex_dev.linter.spi``. Importing the
        SDK or using its standalone UI walker does not require Dev.
    """
    try:
        from scitex_dev.linter.spi import ProviderReplacement
    except ImportError as exc:
        raise ImportError(
            "The scitex-sdk UI linter provider requires scitex-dev>=0.62.4.dev0 "
            "with the declared provider replacement SPI. Install compatible "
            "scitex-sdk[cli] and scitex-dev builds together; standalone SDK UI "
            "use does not require this optional tooling."
        ) from exc

    return {
        "rules": list(build_rules().values()),
        "call_rules": {},
        "axes_hints": {},
        "checkers": [],
        "replaces": (
            ProviderReplacement(
                distribution="scitex-ui",
                entry_point="ui",
                value="scitex_ui._linter_plugin:get_plugin",
                rule_ids=tuple(f"STX-UI{number}" for number in range(101, 108)),
            ),
        ),
    }


__all__ = ["get_plugin"]
