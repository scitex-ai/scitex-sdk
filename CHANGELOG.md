# Changelog

All notable changes to `scitex-sdk`.

## [Unreleased]

(none yet)

## [0.3.16] - 2026-10-31

Picker disabled-with-reason contract (PR #90): `ProjectEntry` gains
`disabled`/`disabled_reason` (absent by default, legacy-safe); the scoped
listing advertises `user_scope_disabled_reason` so a host can grey out All
Projects instead of hiding it, and both views refuse disabled ids and
disabled user-scope with 403 on a single provider read. TS renders disabled
rows greyed (`aria-disabled` + tooltip) and refuses them on
command/click/keyboard; non-string reason fails closed.

## [0.3.15] - 2026-10-24

UA-native controls follow the app theme (PR #87, operator 2026-10-24):
light/dark palettes declare `color-scheme` so select popups, checkboxes,
radios, and scrollbars render in the app theme instead of the OS default
(bright dropdown in dark mode). 2 new branding tests.

## [0.3.14] - 2026-10-23

Shared scrollbar surface + shell-head wiring (operator 2026-10-23):
`shell/scrollbars.css` paints the default scrollbar for every scroll
container from workspace tokens (thumb/border-default, track/bg-secondary,
hover/border-hover), `color-scheme: light/dark` per theme, wired into
shell.css/all.css bundles AND loaded in `standalone_shell.html` right
after theme.css (leaf pages include shell files individually, never the
bundles — bundle-only wiring reached zero pages). New linter STX-UI115
(warning) flags leaf-local scrollbar colouring; STX-UI116 covers
short tab titles.

## [0.3.13] - 2026-10-23

Tab chrome SSOT, short titles + official mark (operator 2026-10-23):
`shell_title` strips a `SciTeX ` prefix (tab carries no brand text —
the favicon IS the brand; project name lives in the app page), new
linter STX-UI116 (warning) flags hardcoded `SciTeX `-prefixed
`data-app-title` / `<title>` in templates, and the canonical favicon is
the official white-on-navy mark (same snake geometry, no dev-vs-prod
conditional; PNG set regenerated).
- Leaf-declared launcher `group` (operator 2026-10-23): optional manifest
  field `foundation` | `work` | `publication` (closed enum, typo is a
  validator ERROR; omitted = host keeps existing grouping), readable at
  runtime via `ScitexAppConfig.app_group`. Tile labels go short
  (`Cards`, `Agent Container`, `Storage`, `Scholar`, `Stats`, `FigRecipe`,
  `Writer`): the `SciTeX ` prefix is now a validator ADVISORY, and tile
  label vs in-app header title are independent strings. Leaf value edits +
  hub launcher dedup (agent-container WORK duplicate dropped) are App-lane
  execution.

## [0.3.12] - 2026-10-22

Identical-row pack (PR #73): STX-UI112 hardcoded tab titles, UI-113
AppHeader selector overrides, UI-114 parallel button bases; scoping
fixes (Django comments, block comments, vendor/_sphinx/test dirs, hub
_native hatch, directional-only UI-111). SDK inspector skips the global
header subtree (PR #69). Layout doctrine: main content vs Details pane.

## [0.3.11] - 2026-10-22

Project picker on the SDK App (PR #66): Writer-shaped project-scoped
picker in the AppHeader slot, "not selected" default, resume-on-change
prefills the scaffold target. Drift enforcement pack (PR #70):
STX-UI108..113 — leaf-local header, hub duplicate manifests (label/icon
only), hardcoded launcher icons (hub_native hatch for chat/settings),
directional !important (display toggles out of scope), hardcoded tab
titles, AppHeader selector overrides; vendor/_sphinx trees unscanned;
doctrine + 135 linter tests.

## [0.3.10] - 2026-10-20

Naming contract draft + SDK App GUI parity (PR #59): `APP_NAMING_CONTRACT.md`
(slug is mount leaf, label family form advisory, AppConfig namespaced),
validator slug-format error + label advisory, wizard mounts shared AppHeader.
Operator label decisions (PR #61): SDK tile `SDK`, renames recorded for
Storage/Scholar/Stats. Leaf icon ownership (PR #63): SDK tile
`fa-wand-magic-sparkles`, contract rule 6, wizard full-pane width.
Favicon SSOT (PR #64): canonical SVG + PNG set (16/32/180/192/512),
branding partial emits SVG + PNG alternate + apple-touch-icon, validator
favicon-drift advisory.

## [0.3.9] - 2026-10-20

Underline-only selected tab in theme `--accent` (PR #60): selected tab
is now underline-only (SciTeX navy in light theme, gold in dark) with
no box, no surface tint, and no weight change. Applied to
`content-tabs.css` and `panes.css` together so the selected look does
not fork by viewport. Contract tests repinned; a11y half
(`aria-selected`, roving tabindex, outside focus ring) unchanged.

## [0.3.8] - 2026-10-19

SciTeX SDK App as canonical custom-app creation (PR #57): creator
product renamed (manifest label, AppConfig verbose_name, CLI/skill copy;
slug, URLs, DB label unchanged); scaffolds emit `mount_policy
login_required` by default; shared `.stx-layout-fill` utility; stale
hub-mount claims fixed. Plus appmaker shared SSoT header row in the
create-app scaffold (PR #54) and `--bg-primary` theme alias for both
shell themes (PR #55).

## [0.3.7] - 2026-10-19

Standardized selected-tab state in the shared Tabs primitive (PR #53):
selected = subtle surface + brand-blue text + semibold + 2px underline
indicator read from `aria-selected`; new `css/app/content-tabs.css`
shared primitive with `panes.css` phone tab bar aligned to the same tokens.

## [0.3.6] - 2026-10-15

Declared UI provider transition (PR #38): canonical SDK replacement of the
legacy UI linter provider, the compatible Dev provider SPI required in every
SDK tooling extra, and import-boundary tests isolated from adjacent installed
providers.

## [0.3.5] - 2026-10-12

Identity re-export of `ScitexAppConfig` at the `scitex_sdk.app` root
(lazy, Django-free plain import preserved; PR #50) — the public
migration target for consumers subclassing the leaf AppConfig.

## [0.3.4] - 2026-10-09

Fail-closed MCP backend selection on file tools, default local (PR #43);
SDK UI ships under the `scitex_sdk_ui` label, migration-free, resolving
the retired scitex_ui label collision (PR #44).

## [0.3.3] - 2026-10-09

Leaf API endpoint successors (PRs #39/#40/#41, re-plan of closed #33/#34/#36):
opt-in leaf API admission with deny-before-import (#39); shared project
picker commands and configurable shortcuts (#40); agent envelope,
request-bound scope, companion expansion, canonical chat registration (#41).
App contract takes the namespaced `scitex_sdk_app` label coexisting with
the persisted `scitex_app` chat identity (lead call option (a)).

## [0.3.2] — 2026-10-03

### Fixed
- FileSystemBackend containment is component-based: sibling-prefix escapes
  (`../project-other/`) are refused on read/write/list/delete/rename/copy,
  and the tree-listing fallback validates through the same containment while
  iterating the validated target with logical alias-namespace metadata.
- `get_files(backend="local"/"filesystem")` selects the filesystem backend
  explicitly, even under ambient `SCITEX_API_TOKEN`; custom registration
  still wins and cloud auto-selection is unchanged.
- `project_access(write=True)` refuses a non-explicit-True grant before
  project-path resolution and revalidates after; missing/raising permission
  checks map to `CapabilityUnavailable`.

### Added
- Optional tagged project-scope capability: `ProjectSelection`,
  `ScopedProjectProvider`, `supports_scoped_capability`, and
  `scoped_project_listing_view` (allow_user_scope advertisement, tagged
  commit via one `remember_scope`, legacy paths byte-compatible).
- Narrow generic `plugins.leaf_declarations` accessor for Hub consumers
  (caller-named attributes, absence tolerated, `LeafContractError` on
  invalid values).

## [0.3.1] — 2026-10-03

### Fixed
- Serve packaged static assets from the standalone Django development server
  when DEBUG is false, using the existing `--insecure` runserver option.
- Allow read-only template context resolution with explicit `remember=False`.
  Omitted arguments retain the existing project-selection persistence behavior.
- Preserve the selected user/application scope and wait for successful project
  persistence before updating the active project.
- Avoid duplicate shared project-picker catalogs while retaining translations.

## [0.3.0]

### Changed

- Move App and UI implementations, templates, assets, translations and skills
  into `scitex_sdk.app` and `scitex_sdk.ui`; the SDK no longer imports or
  requires the retired App/UI distributions.
- Version both components with the SDK distribution. Preserve existing Django
  database labels, chat migration identity, template blocks and environment
  settings while migrating Python and template/static resource paths.
- Ship the frontend as `@scitex/sdk` inside the Python package, with concrete
  component exports and a shared package directory lookup.
- Provide `scitex-sdk app` and `scitex-sdk ui` CLI groups alongside the creator
  wizard and GUI lifecycle. Generated apps use SDK contracts and shell
  templates in both standalone and plugin modes.
- Verify source/sdist/wheel package bytes, frontend exports and version identity
  before publishing. Run full source and installed-wheel suites, strict access
  controls and the frontend checks on pull requests and release branches.
- Normalize optional host project aliases only to IDs in the request's
  accessible project list, before consulting storage or remembering a selection.

### Fixed

- Reject missing, empty, non-string and malformed project-selection POST input
  before creating or consulting a provider. Invalid submissions cannot fall
  back to a stored project. Ordinary navigation without an explicit selection
  retains its authorized stored-project fallback.
- Extract the matching version's changelog entry for GitHub release notes.

### Release gates

- The `project` and `all` extras require a genuine public scitex-dev>=0.62.0
  release. Publication also requires a normal built-wheel `[all]` installation,
  `pip check` and direct SDK ownership inspection.
- Sequential SDK publication reports any transitive predecessor packages as
  `DEPENDENCY_RETIREMENT_NOT_READY`. The separate strict retirement workflow
  still requires genuine canonical consumer releases and clean public graphs;
  SDK publication and the public App/UI repository archives do not certify
  completed consumer migration or deployment.

## [0.1.0] — 2026-09-14

### Added
- `scitex_sdk.app` — facade re-exporting `scitex_app`'s documented public
  surface (18 names) **by identity** (`scitex_sdk.app.X is scitex_app.X`).
- `scitex_sdk.ui` — facade re-exporting `scitex_ui`'s documented public
  surface (5 names) by identity.
- `tests/test_facade_identity.py` — asserts every re-export is the identical
  object as the original (the bar that makes the consumer import rewrite
  mechanical + behavior-neutral).

### Notes
- The facade `depends on` `scitex-app>=0.24.0` + `scitex-ui>=0.20.3` (the
  published floors); it does not vendor them yet.
- No consumer-visible behavior change: `scitex-sdk` is additive. The original
  `scitex-app` / `scitex-ui` distributions are untouched at this step; they
  become thin compat shims only in a later step.
- Facade-first decision + the app/ui boundary-kept-inside-the-SDK rule: ADR
  0001 (scitex-app), ADR 0003 (scitex-ui).
