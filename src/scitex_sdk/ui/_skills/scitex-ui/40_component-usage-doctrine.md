---
description: |
  [TOPIC] SciTeX-UI component-usage doctrine
  [DETAILS] Adoption rules every app-builder agent follows: use scitex-ui
  components, never hand-roll vanilla &lt;select&gt; / native scrollbars /
  raw-hex CSS / shell-CSS edits. Maps directly onto the UI-101..107 lint
  rules shipped by `scitex-ui._linter_plugin`.
tags: [scitex-ui-component-usage-doctrine, lint]
---

# SciTeX-UI Component-Usage Doctrine

How an app-builder agent (or human) writes scitex-ui-consuming UI without
violating the shared foundation. Mirrors what `scitex-sdk ui lint` and the
`scitex_dev.linter.plugins` entry-point check, so the wording here IS the
violation message you'll see.

Reference inventory: see `32_frontend-components.md` (per-component
quick-start) and `34_frontend-components-theme.md` (theme tokens).
This file is the **rule list** — what NOT to do, and what to do instead.

---

## Core doctrine

1. **Use scitex-sdk ui components — don't hand-roll** equivalents in your
   app's `static/<app>/**`. `Dropdown` over vanilla `<select>`,
   `DataTable` over hand-rolled tables, `ConfirmModal` over bespoke
   dialogs, `Tooltip` over custom hover popovers, `ThemeProvider` over
   reading the dark/light class manually.
2. **Theme through tokens** (`var(--text-primary)`, `var(--bg-surface)`,
   `var(--border-default)`, the `--workspace-*` and `--status-*`
   families, the per-app `--app-accent-<app>` accents). Raw hex /
   `rgb()` literals in app CSS are a doctrine violation.
3. **Do not modify shared foundation CSS** from a consumer repo —
   `scitex_sdk/ui/css/shell/*` and `scitex_sdk/ui/css/primitives/*` are the
   ecosystem's shared theme surface (operator directive 13298). Touching
   them from an app PR is an ERROR-level violation.
4. **Don't copy scitex-sdk ui CSS into your `static/<app>/`** — import the
   stylesheets via `<link>` / `@import` instead. Copies drift; imports
   stay synced.
5. **Scrollbar styling**: scitex-sdk ui deliberately does NOT export
   `--scrollbar-*` tokens (chrome quirks vary by browser/OS). Consumers
   define their OWN scrollbar custom-properties LOCALLY and back them
   with workspace-border tokens. Raw hex inside scrollbar rules is a
   violation.

---

## Rule reference

The lint plugin ships these 5 rules via the
`scitex_dev.linter.plugins` entry-point. `scitex-sdk ui lint <path>` walks
`*.css`, `*.html`, and `*.tsx` files under the given path and emits a
violation per match.

### UI-101 — `vanilla-select-no-theme-opt-in` (WARN)

A `<select>` element appears in `*.tsx` / `*.html` under `static/<app>/`
without a `data-app-themed` attribute and without a sibling `body select`
themed-styling rule in the adjacent CSS. Native `<select>` widgets render
OS-default colours (white on dark themes) and break visual cohesion.

**Fix**: use `scitex_sdk.ui.Dropdown` instead. If you must use a native
`<select>` (printer dialog, legacy form), add `data-app-themed="true"`
and ship a `body select { background: var(--bg-surface); color:
var(--text-primary); border: 1px solid var(--border-default); }` rule.

### UI-102 — `raw-hex-in-app-css` (WARN)

A `#xxx`, `#xxxxxx`, `#xxxxxxxx`, or `rgb(...)` / `rgba(...)` literal
appears in a `*.css` file under `static/<app>/**` outside a scrollbar-var
declaration that references another `var(...)`.

**Fix**: replace the literal with the matching theme token
(`var(--text-primary)`, `var(--bg-surface)`, `var(--border-default)`,
`var(--status-success)`, etc.). For app-specific accents, use
`var(--app-accent-<your-app>)`.

### UI-103 — `copied-scitex-ui-css` (WARN)

A `*.css` file under `static/<app>/` contains a rule-signature
fingerprint that matches a known scitex-sdk ui shell/primitive CSS rule —
i.e. the file is a copy/paste of shared styling rather than an import.

**Fix**: delete the local copy and import the scitex-sdk ui stylesheet:
```html
<link rel="stylesheet" href="{% static 'scitex_sdk/ui/css/shell/theme.css' %}">
```
Copies drift the moment scitex-sdk ui ships a theme tweak; imports stay
synced.

### UI-104 — `consumer-touched-shell-or-primitives` (WARN → ERROR next release)

A consumer repo's PR diff modifies `scitex_sdk/ui/css/shell/*` or
`scitex_sdk/ui/css/primitives/*`. The shell + primitives layers are the
**shared foundation** of every SciTeX app; per operator directive 13298
they may only be edited from inside scitex-sdk ui itself (additive PRs to
scitex-ui, with sign-off).

**Flip date**: this rule starts as `WARN` in scitex-sdk ui 0.6.0 and
**flips to `ERROR` in scitex-sdk ui 0.7.0** (standard adoption ramp). Plan
your migration off shell/primitive edits in the WARN window.

**Fix**: do not edit shared shell/primitive CSS from your consumer repo.
If a token is missing, file an additive request against scitex-ui
itself.

### UI-105 — `scrollbar-raw-hex` (WARN)

A `::-webkit-scrollbar-*` rule or `scrollbar-color: …` declaration in a
consumer `*.css` uses a raw hex / `rgb(...)` literal instead of a
`var(...)` reference.

**Fix**: define consumer-local scrollbar vars backed by
workspace-border tokens, then use them:
```css
:root {
  --scrollbar-thumb: var(--workspace-border-default);
  --scrollbar-track: var(--workspace-bg-secondary);
}
.my-app, .my-app * {
  scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
}
.my-app ::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); }
.my-app ::-webkit-scrollbar-track { background: var(--scrollbar-track); }
```

### UI-106 — `long-native-select-no-filter` (WARN)

A native `<select>` with more than 8 literal `<option>` tags and no
Combobox enhancement. Past a dozen options a native picker is
unscannable, and the widget offers only type-to-jump on the FIRST
character.

**Fix**: layer scitex-ui's fuzzy Combobox over it as a progressive
enhancement — the `<select>` stays as the fallback. Opt out with
`data-no-combobox` when a long list is genuinely fine (an ordered list
scrolled by position rather than searched by name).

**Blind spot, stated because absence of a finding is not evidence**: the
option count comes from literal tags in the source, so a `<select>`
filled from `fetch()` looks empty to the rule and will not be flagged
however long it grows. That is why this is a warning.

*(Undocumented here until 0.14.0 — the rule shipped in 0.12.0 and this
page still said "the 5 rules above". A rule an adopter cannot read about
is the same reach defect as one they cannot import.)*

### UI-107 — `absolute-api-url-in-client-code` (ERROR)

A root-anchored API path **literal** — `"/api/…"` or `"/apps/u/…"` — in
`*.ts` / `*.tsx` / `*.js` / `*.jsx` / `*.html`. Correct standalone,
silently wrong once the app is mounted as a scitex-hub built-in.

The rule, its severity rationale, its two exemptions and its blind spot
are documented with the contract they enforce, not here:
**[41_dual-mode-mounting.md](41_dual-mode-mounting.md) § The lint rule.**
Splitting a rule's *what* from its *why* across two pages is how one of
them goes stale, and the mount contract is already that page's subject.

---

## How the linter is wired

`scitex-ui` registers the 7 rules above with scitex-dev's linter via
the canonical entry-point:

```toml
# pyproject.toml
[project.entry-points."scitex_dev.linter.plugins"]
ui = "scitex_sdk.ui._linter_plugin:get_plugin"
```

So they appear in `scitex-linter list-rules` once `scitex-ui` is
pip-installed alongside `scitex-dev`. Active scanning of `*.css`,
`*.html`, `*.tsx` is provided by `scitex-sdk ui lint <path>` (see
`13_cli.md`).

The plugin's `checkers` slot is intentionally empty — scitex-dev's
in-tree checker is Python-AST-only, and the rules above target CSS /
HTML / TSX surfaces that the standalone `scitex-sdk ui lint` walker
covers instead. The two enforcement paths are complementary, not
competing.

---

## Doctrine in one paragraph

If a `static/<app>/` file would make a SciTeX user say *"this widget
looks different from the rest of the app"*, that's a UI-1xx
violation. Use the scitex-sdk ui component, theme through tokens, and
keep shared foundation CSS untouched. The lint rules above are the
shape of that paragraph.
