"""Rule definitions for scitex-ui's UI-101..105 component-usage corpus.

Imported by both:
- :mod:`scitex_sdk.ui._linter_plugin` — the entry-point that registers the
  rules with scitex-dev's linter (visible via ``scitex-linter list-rules``).
- :mod:`scitex_sdk.ui._linter._checker` — the standalone CSS/HTML/TSX
  walker that actively flags violations.

Severity ramp note for UI-104: the rule starts as ``warning`` in scitex-ui
0.6.0 and is scheduled to flip to ``error`` in 0.7.0 (standard adoption
window). Plan migrations off shared-foundation CSS edits in the WARN window.
The flip is documented in the rule message and the doctrine MD; the version
gate is enforced at the rule-build site below.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class _FallbackRule:
    """Soft-fallback Rule shape — mirrors scitex-dev's Rule when absent.

    Lets the standalone walker still produce violations when scitex-dev is
    not installed in the consumer's venv.
    """

    id: str
    severity: str
    category: str
    message: str
    suggestion: str
    requires: str = ""


def _resolve_rule_cls() -> type:
    """Return scitex-dev's canonical ``Rule``, or the fallback when absent.

    Resolved on FIRST USE rather than at module import, and that timing is
    the whole point — see :func:`__getattr__` below for why.

    Absence and breakage are answered separately, because conflating them is
    what made the old code fail silently: ``find_spec`` decides whether
    scitex-dev is installed WITHOUT importing it, and only then is the real
    import attempted. Any error from that import propagates. A cycle, or a
    genuinely broken scitex-dev, is a defect to surface — not an "absent"
    reading that quietly downgrades every rule to the fallback class.

    PS-233 — WHY THIS IMPORT IS GUARDED, AND WHY NOTHING IS DECLARED FOR IT.
    ``scitex-dev`` is a launcher this package talks to over an entry point
    (``scitex_dev.linter.plugins``); it is never a runtime requirement of the
    shipped UI. It is the optional ``[cli]`` extra, and the guard below is the
    contract that keeps it optional: promoting it to
    ``[project.dependencies]`` would make every consumer of scitex-sdk ui install
    the ecosystem's dev toolchain for a capability this code path can do
    without. So the guard is the remedy and the extra stays an extra.

    The guard deliberately does NOT downgrade to ``_FallbackRule``. By the
    time execution reaches the import, ``find_spec`` has already answered the
    absent case — an ImportError HERE means scitex-dev is installed but not
    importable (partial install, mid-upgrade tree, import cycle), which is a
    defect. Converting it into the fallback class is the silent downgrade
    #141 was, and ``test_rule_class_is_scitex_devs_own_when_it_is_installed``
    pins the class identity that would be lost. So the guard re-raises with
    the distribution named and the remedy spelled out: guarded for the static
    scan, loud for the human.
    """
    if importlib.util.find_spec("scitex_dev") is None:
        return _FallbackRule
    try:
        from scitex_dev.linter._rules._base import Rule  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - broken install only
        raise ImportError(
            "scitex-dev is installed but scitex_ui could not import "
            "scitex_dev.linter._rules._base.Rule, so the UI rule corpus "
            "cannot be built from the canonical Rule class. Reinstall "
            "scitex-dev: pip install --force-reinstall scitex-dev"
        ) from exc

    return Rule


def __getattr__(name: str) -> type:
    """Resolve ``Rule`` lazily (PEP 562), breaking a real import cycle.

    Importing scitex-dev's ``Rule`` at MODULE SCOPE — which this module did
    until 2026-08-09 — closes a loop that leaves this package's entire rule
    corpus inactive:

        import scitex_sdk.ui._linter._rules
          -> from scitex_dev.linter._rules._base import Rule   (module scope)
          -> scitex_dev.linter.__init__ runs _register_sweep_cli()
          -> ... which reaches scitex-dev's plugin loader
          -> loader imports scitex_sdk.ui._linter_plugin, calls get_plugin()
          -> get_plugin() needs build_rules from THIS module
          -> but we are still on the import line above: build_rules is
             not yet defined
          -> ImportError, caught by the loader, plugin dropped

    The loader does not fail on that — it warns and carries on, so a run
    with the UI rules ACTIVE and a run with them INACTIVE differ only by one
    line of yellow text (measured: 41 rules / 7 UI vs 34 / 0).

    Deferring to first ATTRIBUTE ACCESS fixes it because every access
    happens inside :func:`build_rules`, i.e. after this module has finished
    initialising — so the loader's re-entrant import finds ``build_rules``
    present. Deferring into ``get_plugin`` instead does NOT work and was
    tried: the loader CALLS ``get_plugin()`` during load, so the import
    lands back inside the same partially-initialised module microseconds
    later.

    Regression-tested by tests/develop/test_linter_plugin_import_cycle.py.
    """
    if name == "Rule":
        cls = _resolve_rule_cls()
        globals()["Rule"] = cls  # cache: __getattr__ is only consulted on miss
        return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(frozen=True)
class UIViolation:
    """One concrete violation emitted by the scitex-sdk ui walker.

    Distinct from scitex-dev's ``Issue`` (which is Python-AST-bound) — a
    ``UIViolation`` is file/line-bound and carries the source-of-truth
    Rule so consumers can format messages the same way the entry-point
    linter does.
    """

    rule: Rule
    path: str
    line: int
    col: int
    source_line: str = ""


# Public category — surfaces in the entry-point listing and shared by
# all 5 rules. Distinct from scitex-dev's "io"/"path"/"plot" categories
# so consumers can mute the UI corpus independently (``--disable UI`` etc.).
CATEGORY = "ui"


def build_rules() -> Mapping[str, Rule]:
    """Construct the rule corpus keyed by rule id.

    Returns
    -------
    Mapping[str, Rule]
        ``{"STX-UI101": Rule(...), ..., "STX-UI105": Rule(...)}``.
    """
    # Bound LOCALLY, not read from module globals. PEP 562's module-level
    # __getattr__ is consulted only for attribute access on the module
    # OBJECT (`_rules.Rule`) — a bare global lookup inside this function
    # goes to globals() then builtins and never reaches it, so relying on
    # the hook here raises NameError. Measured, not assumed: doing exactly
    # that failed all four load orders on 2026-08-09.
    Rule = _resolve_rule_cls()

    UI101 = Rule(
        id="STX-UI101",
        severity="warning",
        category=CATEGORY,
        message=(
            "`<select>` element without theme opt-in — native widget will "
            "render OS-default colours and break dark-theme cohesion"
        ),
        suggestion=(
            "Use scitex_sdk.ui.Dropdown instead. If a native <select> is required "
            "(printer dialog, legacy form), add `data-app-themed='true'` and "
            "ship a `body select { background: var(--bg-surface); color: "
            "var(--text-primary); border: 1px solid var(--border-default); }` "
            "rule. See _skills/scitex-ui/40_component-usage-doctrine.md."
        ),
        requires="scitex-sdk",
    )

    UI102 = Rule(
        id="STX-UI102",
        severity="warning",
        category=CATEGORY,
        message=(
            "raw hex / rgb()/rgba() literal in app CSS — themes drift "
            "when colours are hard-coded instead of token-referenced"
        ),
        suggestion=(
            "Replace the literal with the matching theme token: "
            "var(--text-primary) / var(--text-secondary) / var(--bg-page) / "
            "var(--bg-surface) / var(--border-default) / "
            "var(--status-{success,warning,error,info}) / "
            "var(--app-accent-<your-app>). See _skills/scitex-ui/"
            "34_frontend-components-theme.md for the full token table."
        ),
        requires="scitex-sdk",
    )

    UI103 = Rule(
        id="STX-UI103",
        severity="warning",
        category=CATEGORY,
        message=(
            "scitex-sdk ui shell/primitive CSS rule signature appears in a "
            "consumer's static/<app>/ tree — a local copy of shared styling "
            "that will drift the moment scitex-sdk ui ships a theme tweak"
        ),
        suggestion=(
            "Delete the local copy and import the scitex-sdk ui stylesheet via "
            "<link rel='stylesheet' href=\"{% static 'scitex_sdk/ui/css/shell/"
            "theme.css' %}\">. Copies drift; imports stay synced."
        ),
        requires="scitex-sdk",
    )

    UI104 = Rule(
        id="STX-UI104",
        severity="warning",  # → flip to "error" in scitex-sdk ui 0.7.0
        category=CATEGORY,
        message=(
            "consumer-repo CSS modifies scitex_sdk/ui/css/shell/* or "
            "scitex_sdk/ui/css/primitives/* — these are the SHARED foundation "
            "of every SciTeX app (operator directive 13298). Severity "
            "flips warning → error in scitex-sdk ui 0.7.0; migrate now."
        ),
        suggestion=(
            "Do not edit shared shell/primitive CSS from a consumer repo. "
            "If a token is missing, file an additive request against "
            "scitex-sdk ui itself. See _skills/scitex-ui/40_component-usage-"
            "doctrine.md §UI-104."
        ),
        requires="scitex-sdk",
    )

    UI105 = Rule(
        id="STX-UI105",
        severity="warning",
        category=CATEGORY,
        message=(
            "raw hex / rgb() literal inside a scrollbar rule — themes "
            "drift; scrollbar colours should reference workspace-border "
            "tokens via a consumer-local var indirection"
        ),
        suggestion=(
            "Define consumer-local scrollbar vars backed by workspace-border "
            "tokens:\n"
            "  :root { --scrollbar-thumb: var(--workspace-border-default);\n"
            "          --scrollbar-track: var(--workspace-bg-secondary); }\n"
            "  .my-app, .my-app * { scrollbar-color: var(--scrollbar-thumb) "
            "var(--scrollbar-track); }\n"
            "  .my-app ::-webkit-scrollbar-thumb { background: "
            "var(--scrollbar-thumb); }"
        ),
        requires="scitex-sdk",
    )

    UI106 = Rule(
        id="STX-UI106",
        severity="warning",
        category=CATEGORY,
        message=(
            "long native `<select>` with no way to narrow it — a picker "
            "past a dozen options is unscannable, and the native widget "
            "offers only type-to-jump on the FIRST character"
        ),
        suggestion=(
            "Layer scitex-ui's fuzzy Combobox over it as a progressive "
            "enhancement — the <select> stays as the fallback:\n"
            '  <script type="module" '
            'src="{% static \'scitex_sdk/ui/js/app/combobox.js\' %}"></script>\n'
            "  if (window.STX && window.STX.Combobox) {\n"
            "    document.querySelectorAll('select.my-filter')\n"
            "      .forEach((el) => new window.STX.Combobox({ from: el }));\n"
            "  }\n"
            "Fuzzy is subsequence matching, so `sui` finds `scitex-ui`. "
            "Needs scitex-sdk ui >= 0.12.1."
        ),
        requires="scitex-sdk",
    )

    UI107 = Rule(
        id="STX-UI107",
        severity="error",
        category=CATEGORY,
        message=(
            "root-anchored API path literal in client code — correct "
            "standalone, silently wrong once the app is mounted as a "
            "scitex-hub built-in under /apps/u/<module>/"
        ),
        suggestion=(
            "Join the path onto the mount prefix the server put in the page:\n"
            '  import { apiUrl } from "@scitex/sdk/ui/ts/_base";\n'
            '  await fetch(apiUrl("/api/items"));\n'
            "and have the view declare the prefix:\n"
            "  from scitex_sdk.ui.mount import mount_context\n"
            "  render(request, tpl, {..., **mount_context(request)})\n"
            "apiUrl() THROWS when the marker is absent rather than "
            "defaulting to '/', because a default works standalone and "
            "fails only embedded. Needs scitex-sdk ui >= 0.13.0; see "
            "`scitex-sdk ui skills get 41_dual-mode-mounting`."
        ),
        requires="scitex-sdk",
    )

    return {
        UI101.id: UI101,
        UI102.id: UI102,
        UI103.id: UI103,
        UI104.id: UI104,
        UI105.id: UI105,
        UI106.id: UI106,
        UI107.id: UI107,
    }


#: What this linter CANNOT see. Emitted on EVERY run, clean or not.
#:
#: A check whose output is indistinguishable from a complete one is the
#: defect this exists to prevent: "no violations found" reads as "nothing
#: is wrong" when it may mean "nothing was looked at". scitex-dev made
#: stating the gap in the EMITTED VERDICT a requirement rather than a
#: preference (2026-07-29) — not the docstring, not the card, the output.
#: Their own corpus does the same for unregistered rule categories.
#:
#: Every entry here is a property of the code in `_checker.py`, not a
#: guess. Add one whenever a rule's reach narrows.
COVERAGE_GAPS: tuple[tuple[str, str], ...] = (
    (
        "runtime-generated markup",
        "this is a static text scanner: elements created or populated at "
        "runtime by JS are never inspected. STX-UI106 in particular counts "
        "<option> tags in source, so a <select> filled from fetch() looks "
        "empty to it and will not be flagged however long it gets.",
    ),
    (
        "built output",
        "dist/ and build/ are skipped, so what a consumer actually ships is "
        "not scanned — only the sources it was built from.",
    ),
    (
        "HTML assembled in Python",
        "only .css/.html/.htm/.ts/.tsx/.js/.jsx are read. Markup built by "
        "string concatenation inside .py is invisible.",
    ),
    (
        "URLs built at runtime",
        "STX-UI107 matches a root-anchored path LITERAL. A URL assembled by "
        'concatenation (`"/" + kind + "/items"`) or read from config is not '
        "a literal and is not flagged, so a clean UI-107 run is not evidence "
        "an app is mount-safe. This is the same blind spot as STX-UI106 and "
        "the reason the mount reader THROWS at runtime: the static check "
        "cannot be the only gate.",
    ),
    (
        "comment/exemption detection is line-prefix based",
        "STX-UI107 skips a line whose first non-space characters are //, /*, "
        "* or <!--, and skips a line that also contains `apiUrl(` — because "
        "the correct fix, apiUrl(\"/api/x\"), contains the literal being "
        "flagged. Both tests are per-LINE, so a literal inside a block "
        "comment whose body does not start with * , or an apiUrl() call "
        "split across lines, will be judged wrongly. Measured 2026-07-30: "
        "both of scitex-ui's own two matches were documentation, one of "
        "them the docstring for apiUrl itself.",
    ),
)


def coverage_notice() -> str:
    """Render the always-emitted statement of what was NOT inspected."""
    lines = [
        "NOT EVERYTHING WAS INSPECTED — this verdict covers only what a "
        "static scan of the source can see:",
    ]
    lines += [f"  - {name}: {detail}" for name, detail in COVERAGE_GAPS]
    return "\n".join(lines)


__all__ = [
    "Rule",
    "UIViolation",
    "CATEGORY",
    "build_rules",
    "COVERAGE_GAPS",
    "coverage_notice",
]
