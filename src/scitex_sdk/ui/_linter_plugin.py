"""SDK-owned UI-101..107 component-usage linter rules.

Registered via entry point `scitex_dev.linter.plugins` so the rules
appear in `scitex-linter list-rules` once both `scitex-sdk` and a compatible
`scitex-dev` are installed. The SDK declares the exact predecessor provider
and the complete rule set that installed release advertised (seven rules
from scitex-ui 0.14.0; five or six from older releases); installing any
published UI distribution alongside the SDK therefore keeps one canonical
rule corpus instead of failing the linter.

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

import re
from importlib import metadata

from ._linter._rules import build_rules

#: The retired predecessor distribution whose provider the SDK replaces.
PREDECESSOR = "scitex-ui"

#: Complete rule corpus each published predecessor release advertised,
#: keyed by the first release that advertised it (read from the published
#: wheels' ``scitex_ui._linter._rules``): 0.6.0-0.12.1 UI101-105, 0.13.0
#: UI101-106, 0.14.0-0.23.1 UI101-107; releases before 0.6.0 ship no
#: provider, so the replacement stays dormant for them. scitex-dev accepts a replacement only when
#: it names the predecessor's complete advertised set, so the declaration
#: must follow the installed release. The SDK cannot pin a floor instead:
#: requiring the retired distribution, even optionally, fails the release
#: ownership gate (scripts/ownership_gate.py).
PREDECESSOR_CORPORA: tuple[tuple[tuple[int, ...], tuple[str, ...]], ...] = (
    ((0, 14, 0), tuple(f"STX-UI{n}" for n in range(101, 108))),
    ((0, 13, 0), tuple(f"STX-UI{n}" for n in range(101, 107))),
    ((0,), tuple(f"STX-UI{n}" for n in range(101, 106))),
)

#: First predecessor release whose corpus is the full SDK contract.
FULL_CONTRACT_FLOOR = PREDECESSOR_CORPORA[0][0]


def _release(version: str) -> tuple[int, ...]:
    match = re.match(r"\d+(?:\.\d+)*", version)
    return tuple(int(part) for part in match.group().split(".")) if match else (0,)


def predecessor_rule_ids(version: str | None) -> tuple[str, ...]:
    """Rule IDs the predecessor release ``version`` advertised.

    ``None`` (predecessor not installed) yields the full contract; the
    replacement is then dormant in scitex-dev.
    """
    if version is None:
        return PREDECESSOR_CORPORA[0][1]
    release = _release(version)
    for floor, rule_ids in PREDECESSOR_CORPORA:
        if release >= floor:
            return rule_ids
    return PREDECESSOR_CORPORA[-1][1]


def _installed_predecessor_version() -> str | None:
    try:
        return metadata.version(PREDECESSOR)
    except metadata.PackageNotFoundError:
        return None


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
            "The scitex-sdk UI linter provider requires scitex-dev>=0.62.6 "
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
                distribution=PREDECESSOR,
                entry_point="ui",
                value="scitex_ui._linter_plugin:get_plugin",
                rule_ids=predecessor_rule_ids(_installed_predecessor_version()),
            ),
        ),
    }


__all__ = ["get_plugin"]
