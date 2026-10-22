"""Rule definitions for scitex-ui's UI-101..111 component-usage corpus.

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

    # Drift pack (operator CCT4948-4950): SSOT enforcement. All four are
    # warnings, per UI-107's measured lesson — a rule whose first run is
    # red gets disabled rather than obeyed.
    UI108 = Rule(
        id="STX-UI108",
        severity="warning",
        category=CATEGORY,
        message=(
            "leaf-local `<header>` element instead of the shared AppHeader "
            "primitive (`data-stx-app-header`) — the row forks the moment "
            "the SDK ships a header tweak"
        ),
        suggestion=(
            "Mount the primitive like every other leaf:\n"
            '  <div data-stx-app-header data-app-title="..." '
            '[data-app-version="..."]></div>\n'
            "plus app-header.css and the prebuilt app-header.js module. "
            "No leaf-local `<header>` element. See the SDK App wizard "
            "(scitex_sdk/creator) as the reference adopter. Run "
            "`scitex-sdk ui lint` to find leaf-local headers."
        ),
        requires="scitex-sdk",
    )

    UI109 = Rule(
        id="STX-UI109",
        severity="warning",
        category=CATEGORY,
        message=(
            "hub-side duplicate builtin manifest disagrees with the leaf's "
            "own manifest (label / icon) — the tile renders hub "
            "copy, and the copy has already drifted once (writer label+icon)"
        ),
        suggestion=(
            "Read display metadata from the leaf manifest (the plugin mount "
            "already does) or delete the duplicate so the registry falls "
            "through to it. The leaf manifest is the single source. Run "
            "`scitex-sdk ui lint` (STX-UI109) over the hub tree."
        ),
        requires="scitex-sdk",
    )

    UI110 = Rule(
        id="STX-UI110",
        severity="warning",
        category=CATEGORY,
        message=(
            "hardcoded `icon` in a hub launcher JSON — tiles must render "
            "the leaf manifest icon, never a hub-side glyph"
        ),
        suggestion=(
            "Resolve the icon from the leaf manifest at render time "
            "(registry already carries manifest_icon_fa) and drop the "
            "hardcode. Operator rule: leaf owns icons. Run "
            "`scitex-sdk ui lint` (STX-UI110) to list hardcoded icons."
        ),
        requires="scitex-sdk",
    )

    UI111 = Rule(
        id="STX-UI111",
        severity="warning",
        category=CATEGORY,
        message=(
            "unconditional `!important` directional override (flex-direction "
            "/ flex-wrap) in a file that also carries an @media block — "
            "the override silently beats the responsive rules and the "
            "layout forks by viewport"
        ),
        suggestion=(
            "Scope the override to the breakpoint that needs it (move it "
            "inside the @media block) or drop the `!important` so the "
            "media query can win. See the writer fork that killed its own "
            "600px breakpoint this way. Run `scitex-sdk ui lint` to list "
            "files where a top-level !important beats @media. `display` "
            "toggles are deliberately out of scope: tab-visibility state "
            "is JS-driven, not layout direction."
        ),
        requires="scitex-sdk",
    )

    # Identical-row pack (operator 2026-10-20): title, version and project
    # picker must be the IDENTICAL element across applications — same
    # component, same row height, placement and font size, all from the
    # SDK. All warnings: hub's first run will be red.
    UI112 = Rule(
        id="STX-UI112",
        severity="warning",
        category=CATEGORY,
        message=(
            "hardcoded `<title>` text in a Django template instead of the "
            "shared `{{ app_label }}` title — the tab must read the same "
            "name as the tile (operator: cards showed Card Board for a "
            "Cards tile)"
        ),
        suggestion=(
            "Render `<title>{{ app_label }}</title>` via the shared shell "
            "or `_branding_head.html` partial; pass the manifest label as "
            "app_label from the view. Run `scitex-sdk ui lint` to list "
            "hardcoded tab titles."
        ),
        requires="scitex-sdk",
    )

    UI113 = Rule(
        id="STX-UI113",
        severity="warning",
        category=CATEGORY,
        message=(
            "consumer CSS overrides the shared AppHeader row "
            "(`.stx-app-header*`, `[data-stx-app-header]`) — row height, "
            "placement and font size come from the SDK alone so the "
            "row renders identically in every app"
        ),
        suggestion=(
            "Delete the override; if a token is missing, file it against "
            "scitex-sdk ui. Never restyle the header row per-leaf. Run "
            "`scitex-sdk ui lint` to list AppHeader forks."
        ),
        requires="scitex-sdk",
    )

    UI114 = Rule(
        id="STX-UI114",
        severity="warning",
        category=CATEGORY,
        message=(
            "leaf-local button base style (`.btn { ... }` or bare "
            "`button { ... }`) instead of the shared `.stx-button` / "
            "`.stx-button--primary` primitive — one button look everywhere"
        ),
        suggestion=(
            "Adopt scitex_sdk.ui's `.stx-button` (36px standard height, "
            "themed via tokens) and delete the parallel base. Keep only "
            "app-specific size tweaks where a toolbar genuinely needs "
            "them. Run `scitex-sdk ui lint` to list parallel button bases."
        ),
        requires="scitex-sdk",
    )

    # UI-115 — leaf-local scrollbar colouring: RAW colours
    # (hex/rgb outside var()) in scrollbar rules without the shared
    # shell surface. Token-backed declarations are the fixed state.
    # Never ship per-leaf colours that fork by theme, and never ship
    # an unstyled scroll container that renders OS-default colours.
    UI115 = Rule(
        id="STX-UI115",
        severity="warning",
        category=CATEGORY,
        message=(
            "leaf-local scrollbar colouring (raw `scrollbar-color` / "
            "`::-webkit-scrollbar-*` colour declarations, or no scrollbar "
            "styling at all in a scroll container) instead of the shared "
            "`shell/scrollbars.css` — scrollbars must track light/dark "
            "via the SDK's workspace tokens, not per-leaf literals"
        ),
        suggestion=(
            "Import the shared shell scrollbar surface "
            "(`shell/scrollbars.css`, in the shell.css / all.css bundles) "
            "and delete per-leaf scrollbar colour rules; keep only "
            "width/shape tweaks where a control genuinely needs them. "
            "Run `scitex-sdk ui lint` to list scrollbar forks."
        ),
        requires="scitex-sdk",
    )

    # Short-tab-title rule (operator 2026-10-23): tab and in-app header
    # titles use the SHORT tile form — the favicon carries the brand, a
    # "SciTeX " prefix is truncated noise at 16px, and the project name
    # lives in the app page itself. UI115 is the scrollbar surface rule;
    # this one is UI116 by design.
    UI116 = Rule(
        id="STX-UI116",
        severity="warning",
        category=CATEGORY,
        message=(
            "hardcoded `SciTeX `-prefixed app title (`data-app-title=` or "
            "`<title>`) — tab and header titles use the short tile form "
            "(operator 2026-10-23); the favicon carries the brand"
        ),
        suggestion=(
            "Use the short name (the manifest tile label). For computed "
            "titles, `scitex_sdk.ui.branding.shell_title` strips the "
            "prefix. Run `scitex-sdk ui lint` to list branded titles."
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
        UI108.id: UI108,
        UI109.id: UI109,
        UI110.id: UI110,
        UI111.id: UI111,
        UI112.id: UI112,
        UI113.id: UI113,
        UI114.id: UI114,
        UI115.id: UI115,
        UI116.id: UI116,
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
