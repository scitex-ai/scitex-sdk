# Changelog

All notable changes to `scitex-sdk`.

## [Unreleased]

- Add HOSTED MCP (`scitex_sdk.app.api_mcp_http`, API contract v1 §11): the
  declared operations of the admitted plugins served over MCP Streamable
  HTTP, for agents that know a URL and a key. It is stateless, answers JSON,
  handles `initialize`, `ping`, `tools/list` and `tools/call`, and accepts
  protocol revisions 2025-11-25, 2025-06-18 and 2025-03-26.
  - Every `tools/call` runs `api_exec.execute`, the REST core. A success
    carries the REST body as `structuredContent` and `_meta.request_id`. A
    failure is an `isError` result whose `structuredContent` is the full
    problem object (API-M003/M004).
  - `tools/list` is filtered by the caller's scopes and tier (`public` <
    `member` < `paid`, new `ApiCaller.tier`). A host may raise a tool's tier
    but not lower it (API-M002).
  - Authentication goes through a pluggable authenticator with the
    `SCITEX_API_CALLER` contract. Only Bearer is accepted. A missing or
    invalid bearer gets a 401 with `WWW-Authenticate` (optionally naming the
    RFC 9728 resource metadata). Other checks: `Origin` (403), method (405)
    and `MCP-Protocol-Version` (400).
  - Django: `mcp_urlpattern()` mounts `api/v1/mcp` with the REST hooks.
    `protected_resource_metadata()` builds the RFC 9728 document.
- MCP tools derived from operations now carry `outputSchema` (the REST
  envelope around the declared response), `title` and behaviour
  `annotations`.

## [0.4.1] - 2026-11-28

- Add the API INVENTORY (`scitex_sdk.app.api_inventory`): one deterministic
  listing of every API endpoint and MCP tool, tagged with the API contract v1
  rule ids it violates (`docs/design/api-contract-v1/01-rules.md`): D001
  not generated from an operation, D005 dynamic dispatcher, R001-R004 URL
  grammar / casing / plural / trailing slash, V002 verb in path, A001 no
  Bearer credential, A004 anonymous write, E001 not problem+json, E003 HTML
  or login redirect on an API path, T001-T003 tool name / REST<->MCP 1:1 /
  re-namespaced tool, plus the inventory-only X001 (hub view calls leaf
  logic).
  - Per package: `api_click_group(package=...)` gives any leaf CLI
    `<pkg> api list [--format json|csv|md] [--strict]`: its declared
    `scitex.apis` operations (checked with `scitex_sdk.testing.api_contract.check_plugin`,
    the same static rules as the contract test) plus its FastMCP tools.
  - Global: `aggregate()` composes the per-package listings with a host's
    Django URLconf (every pattern via `get_resolver()`: methods, credential
    modes, permission, CSRF exemption, owner hub/leaf, leaf modules a hub view
    calls), ASGI mounts (`/mcp`, websockets), the hosted MCP aggregate
    (namespace and owner per tool) and an optional GET-only live probe. Front
    end: `scitex-sdk api inventory [--django-settings ... --asgi ...
    --hosted-mcp ... --probe-base ...] --output-dir DIR` writes
    `inventory.json`, `inventory.csv` and `index.md`.
- `scitex-sdk api list` lists the SDK's own declaration (`sdk.skills.list`).
- Contract findings for declared operations come from
  `scitex_sdk.testing.api_contract.declaration_violations` (the static subset
  of the contract test and the Dev `PS-SDK-API` audit), so a hand-written
  plugin is reported as API-D001 exactly as the contract test reports it.

## [0.4.0] - 2026-11-28

API contract v1 enforcement (docs/design/api-contract-v1/, workstream W1).

- **Rule ids on every declaration-time refusal.** `scitex_sdk.app.api_rules`
  registers the contract rules; the operation layer raises
  `ApiContractViolation` (an `ApiPluginContractError`) with `.rule`, and the
  message starts with the id: `[API-R003] clew.data.list: resource 'data' must
  be a plural noun`. New declaration checks: reserved package names
  (API-R006), snake_case fields and enum values (API-F001), `<package>.<snake>`
  error codes (API-E002), page limits ≤ 200 and every `list` paginated
  (API-G001), a Job schema with `id` and `state` (API-J001), closed rate-class
  and compute-cost sets (API-H002, API-K001), `module:function` handlers
  (API-D006), contract major (`build_plugin(..., contract="1")`, API-D003),
  duplicate tool names (API-T001).
- **Breaking:** `compute_cost` must be `light|standard|heavy` and `rate_class`
  `anonymous|standard|search|bulk|interactive` for operation-built plugins; a
  `list` operation must be paginated.
- **Public operations** (API-A004): `ApiOperation(public=True)` for a
  side-effect-free read that is not project-scoped. Served without a
  credential; a presented-but-invalid bearer is still 401.
- **Contract test** `scitex_sdk.testing.api_contract`: `assert_contract(PLUGIN)`
  runs the static rules, MCP 1:1 (API-T002), OpenAPI validity (API-O002), and
  probes every operation over the real SDK serving path (401/403/405/400
  problem+json, `X-Request-Id`); `compare(previous, current)` enforces
  additive-only change (API-C001).
- **Dev audit rule `PS-SDK-API`**: the same static rules over source
  declarations (no consumer import); a hand-written plugin reports API-D001.
- **Legacy-route deprecation headers** (API-H003):
  `scitex_sdk.app.api_deprecation.LegacyApiDeprecationMiddleware` adds
  `Deprecation` (RFC 9745), `Sunset` (RFC 8594, beta launch + N months; omitted
  while `SCITEX_API_BETA_LAUNCH_DATE` is unset) and `Link` headers.
- A trailing-slash `/api/v1/` path answers a 404 problem naming the canonical
  path (API-R004); refusals of off-grammar plugins log at ERROR.
- The SDK's own API is now an operation plugin: entry point `sdk`,
  `GET /api/v1/sdk/skills` (public, paginated, MCP `sdk_skills_list`). It was
  previously a hand-written route that the generic host mount refused.

## [0.3.26] - 2026-11-27

- Add the host STORAGE GATE capability: `scitex_sdk.host.storage_budget(request,
  project)` reads the host's storage/spend report (`StorageBudget`: used, quota,
  per-file limit, spend level/percent, link) and
  `require_storage_write(request, project, incoming_sizes=...)` asks the host to
  admit a write before it happens, raising `StorageRefused` (402 spend controls /
  413 quota, with the host's `code` and `link`). Hosts implement it through the
  `SCITEX_STORAGE_GATE` setting (`budget(project_id, request)`,
  `require_storage_write(project_id, request, *, incoming_sizes)`). A host without
  a gate answers `CapabilityUnavailable`, so a leaf refuses to write rather than
  assume it may. Read-only project access is refused (403) before the gate.

- Add the API OPERATION layer (`scitex_sdk.app.api_ops`): a leaf declares
  `ApiOperation(package, resource, verb, handler, ...)` and the SDK derives the
  normalised URL `/api/v1/<package>/<resource>[/{<resource>_id}][/<action>]`,
  the scope `<package>:<resource>:<read|write>`, the MCP tool name
  `<package>_<resource>_<verb>`, status codes (201 create, 202 job, 204
  delete), cursor pagination and the project parameter (`owner/slug`), as
  ordinary `ApiRoute`s of an `ApiPlugin`. `ApiRoute` gains an optional
  `summary`.
- Add generic serving (`scitex_sdk.app.api_serve`): one `api_urlpatterns()`
  line mounts every admitted `scitex.apis` plugin at `api/v1/<id>/` in any
  Django host, with no plugin-specific host code. Auth, scopes, rate limits,
  metering and idempotency storage are host hooks (`SCITEX_API_CALLER`,
  `SCITEX_API_RATE_LIMITER`, `SCITEX_API_METER`,
  `SCITEX_API_IDEMPOTENCY_STORE`, `SCITEX_API_TRUSTED_DISTRIBUTIONS`). Errors
  are RFC 9457 problem+json (never HTML or a login redirect); write operations
  require `Idempotency-Key` and replay; session writes pass CSRF. A plugin off
  the operation grammar is refused, not mounted.
- Add the transport-neutral executor (`scitex_sdk.app.api_exec`) and MCP
  generation (`scitex_sdk.app.api_mcp`): every operation is one FastMCP tool
  whose input schema is the REST request schema, run through the same
  executor, so REST and MCP map 1:1.

## [0.3.25] - 2026-11-20

- Render project pickers and provider metadata in explicitly configured standalone
  mode without requiring a login session. Hosted anonymous renders still hide
  these controls; provider, project and storage authorization are unchanged.
- Honor the explicitly registered host API authenticator when authorizing a
  project capability. Bind its confirmed identity to the current request before
  project/storage resolution; preserve session precedence, standalone behavior,
  inaccessible-project refusal and write checks. Credential validation and key
  permissions remain the host's responsibility.

- Declare the UI linter provider replacement for the installed scitex-ui
  release's complete advertised rule set (UI101-105 up to 0.12.1, UI101-106
  in 0.13.0, UI101-107 from 0.14.0). A stale scitex-ui next to the SDK no
  longer makes scitex-dev refuse to run any linter; the SDK still never
  requires the retired distribution.

- Use the Node 24 Python setup action and verify its selected executable before
  creating each CI/release environment. Preserve source, wheel, frontend and
  strict access gates across Python 3.11–3.13.

## [0.3.24] - 2026-11-12

- Require Config 0.3.8 or newer so minimum-dependency installations on Python
  3.10 use its supported PyYAML dependency range.
- Read Django-rendered CSRF tokens before falling back to the CSRF cookie, so
  project and scope changes work with HttpOnly cookies. Export the shared
  frontend helper and update both shipped picker bundles.
- Route CPU validation and release jobs through shared organization admission
  and the quarantine-aware runner pool. Preserve fork refusals, test coverage,
  dependency checks and publication ordering.
- Clarify test contracts without changing their refusal conditions; add real
  HTTP controls for CSRF headers and workflow routing regression checks.

## [0.3.23] - 2026-11-04

- Declare the existing canonical SDK CLI through the installed `scitex.cli`
  provider metadata (`sdk = "scitex_sdk.cli:main"`). Keep the existing
  `scitex-sdk` launcher, Python API, App/UI assets, and dependency graph.
- Document declaration discovery and independent operator exposure settings;
  publication supplies capability metadata and does not force a client to load it.

## [0.3.22] - 2026-11-04

- Add opt-in uniform content-tab widths through the shared tab primitive and
  `--stx-content-tabs-tab-width`. Preserve default sizing and semantic selection
  colors; long labels wrap and overflowing rows scroll horizontally.
- Verify the public CSS entry point, custom widths, minimum hit areas and
  unchanged defaults in desktop/mobile light/dark browser checks.

## [0.3.21] - 2026-11-04

- Recognize generated CSS from nested Vite projects through their enumerated
  package build command, static output directory, manifest and authored inputs.
  Keep ambiguous or unsupported builds subject to ordinary inspection, and
  continue checking authored header and shell styles.

## [0.3.20] - 2026-11-04

- Build source-proven Web API descriptors into wheel dist-info through a shared backend-neutral producer and Hatch adapter; reject competing metadata producers without importing consumers.

- Preserve documentation ownership across host module replacement: prefer the
  closest explicit pane (including empty suppression), prune detached header
  instances and adopt only an unambiguous picker in an explicit owning region.

- Add an optional host-supplied API documentation action to the canonical
  TypeScript/React header, preserving project-picker state and refusing unsafe
  URLs. The SDK supplies no host route or domain capability catalog.

- Recheck declared Web APIs after staged or unstaged handler/descriptor deletions,
  while preserving the chrome hooks' changed-file policy. Document the five
  discovery paths and distinguish source contracts, installed providers and
  host admission.

- Resolve the public standalone-host helper lazily so descriptor imports do not initialize standalone logging or user directories; preserve function identity and discovery.

- Declare an opt-in read-only Web `skills` route over actual bundled SDK/App/UI skill IDs, with a pure Python resource reader and no host/user discovery.

- Add SDK-owned `PS-SDK-WEB` source descriptor/handler checks through the existing Dev project-audit and native-hook providers, without importing or enabling consumer APIs.
- Appmaker CSS validator gains tier 2d: margin/padding set on the app
  container itself (`#main-content`, `#app-mount`, `.ws-module-pane`) is
  reported, since it shrinks the largest app content. Zero resets stay
  silent, as do margins on the app's own children; bare `var()`/`env()`
  values are a declared blind spot. Calibrated silent over FigRecipe,
  Writer, Stats, and SDK CSS (123 files).
## [0.3.19] - 2026-11-03

- Recognize Vite builds through their real, owned manifest source inputs,
  including host `apps/**/static/**/ts` layouts. Generated bundles containing
  shared SDK header styles defer to authored source inspection.
- Keep unbound manifests, ignored or symlinked inputs, escaping/unlisted outputs
  and authored header overrides subject to the existing ownership checks.

## [0.3.18] - 2026-11-02

- Bound phone content-only shells to remaining viewport flex space below the
  natural host header when AI, Files and Viewer are explicitly unused; keep
  used utility stacks reachable by page scrolling.
- Restrict mobile sizing, gestures and collapse preferences to shell-owned
  utility sidebars. Nested app Details panes keep their state, dimensions and
  ARIA ownership across breakpoints and gestures.
- Content-fingerprint the two changed shell stylesheets and mobile runtime.
  Add real Chromium frame/scroll/ownership regressions to the existing automatic
  frontend gate, plus rendered-template hash checks.
- Preserve the seven unrelated source/bundle drifts and existing strict audit
  debt as separate work; this narrow release rebuilds only mobile-swipe.
- Public availability requires the normal release workflow and independently
  verified PyPI artifacts. Feature and metadata CI alone are not evidence of
  publication.

## [0.3.17] - 2026-11-01

- Expose request-local project view selections independently of remembered
  preference; authorize project access with optional `remember=False`.
- Expose public PDF page surfaces and viewport coordinate conversion, with
  opt-in selectable text and link layers. Existing two-argument render
  callbacks remain supported.
- Add the shared DataTable, focus-aware filter fields, and source ownership
  checks. Their public UI builds ship in the Python wheel.
- Published to PyPI on 2026-11-01 UTC. LivePaper 0.2.20 and Writer consumers
  use the released SDK APIs; source installation alone is not publication
  evidence.

- Normalize AppHeader and ProjectSelector typography independently of page root
  fonts, and limit Creator button styles to its action rows. Add Chromium
  regressions for both themes, phone/desktop layouts and scope availability.

- Add opt-in main-details panes layout with a shared 320px Details default,
  responsive bounds and phone width, and collapse behavior preserving host
  restored inline sizes. See docs/ui/main-details-panes.md; this opt-in mode remains experimental.

- Creator starter choices and primary buttons use the semantic navy/gold primary-action roles; the
  in-app header reads SciTeX SDK while launcher labels remain SDK.

- AppHeader auto-mount immediately places an existing direct SDK project picker
  in its canonical slot, preserving the control and avoiding a second header row
  while leaf viewer modules load.

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
