# Changelog

All notable changes to `scitex-sdk`.

## [Unreleased]

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
