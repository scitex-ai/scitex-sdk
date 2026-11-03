# Identical in-app headers

`AppHeader` and `ProjectSelector` own the in-app header. An app supplies its
translated label, package version, and host-provided project capabilities.
It must not supply a separate header template or override the shared metrics.

The source owners are `ui/css/app/app-header.css`,
`ui/css/app/project-selector.css`, and their corresponding TypeScript
components under `src/scitex_sdk/ui/static/scitex_sdk/`.

The shared header explicitly sets its font family and line height. Title and
project-option text are 14px; the version and option detail are 12px. These
component sizes do not depend on a page's 14px or 16px root font size. Browser
zoom still scales them. Desktop picker triggers are 36px high, with 44px
targets on phones or coarse pointers. The shared responsive rules own wrapping.
Colors continue to use the shared semantic palette in both themes.

## Host-supplied API documentation action

The host may supply `apiDocsUrl` to the TypeScript or React `AppHeader`, or
stamp `data-stx-api-docs-url` on its mount or an ancestor. The shared header
uses its existing href-action primitive to show an accessible **API** link.
`apiDocsLabel` supplies a translated accessible label. Updating the URL keeps
the same project picker and actions; `null` or an empty value hides the link.
No URL means no action. The SDK never guesses a package, host route or API
endpoint, fetches a catalog, or enables a handler.

Hosts normalize the owning distribution from their application registry and
choose the documentation URL. A package-scoped page must distinguish missing
providers, declared schemas, host admission and actual live availability.
Origin-relative and HTTP(S) links are supported; script/data URLs, userinfo,
protocol-relative links and control characters are refused.

The prebuilt `js/app/app-header.js` comes from `scripts/build-ui.mjs`.
Standalone pages should load it through `{% app_static %}` so its content
fingerprint changes with this implementation. Hosts bundling React/TypeScript
must rebuild their own frontend against the matching installed SDK package.

Keep content CSS scoped to content controls. For example, Creator styles
`.stx-actions > button`, rather than every button under `.stx-creator`: the
broader selector also restyled the shared picker trigger and its options.
Do not redeclare semantic color tokens as self-references; CSS treats those
as cycles and invalidates their inherited values.

## Availability is data

The host provides `ProjectEntry.disabled` and `disabled_reason` for individual
projects. A scoped provider can return `user_scope_disabled_reason(request)`
for All Projects. Unsupported choices stay visible with a reason and native
disabled behavior. The SDK listing/remember views also reject unavailable
choices server-side. Never infer All Projects from a missing or empty id.

All four capability combinations must work: user/project both available,
only user available, only project available, and neither available. Scope
support must describe the actual backend capability of the app and host.

## Browser verification

Run `npm ci`, `npx playwright install chromium`, then `npm run test:headers`.
The frontend workflow runs this Chromium contract alongside its existing jobs.
`SCITEX_TEST_CHROMIUM` may name an existing Chromium executable locally.

The test uses the shipped SDK CSS, prebuilt AppHeader/ProjectSelector modules,
and Creator stylesheet. It checks conflicting page typography, both themes,
desktop/phone layouts, popup option styles, and all four availability states.
Changing text labels and versions must not change those style metrics.

Integration verification must also visit the real mounted apps and compare
their computed styles: a fixture alone cannot detect a leaf's later CSS
override or a stale bundled SDK stylesheet. Keep installed SDK sources,
generated frontend bundles, and served static assets consistent. Use the
existing `app_static` tag for directly linked assets so CSS changes receive
a content-derived URL.

For an authorized development host, run the real app matrix:

```bash
SCITEX_HEADER_BASE_URL=https://your-authorized-host.example \
SCITEX_HEADER_STORAGE_STATE=/private/playwright-session.json \
npm run test:headers:live
```

This opens the normal apps and dropdowns at desktop and phone sizes, changes
the theme only in that browser document, and compares header/picker styles.
It never chooses a project or saves a theme preference. Apps can still make
their normal background requests while loading. Override the app-relative
route list with the JSON array `SCITEX_HEADER_ROUTES` when checking another
installation. The report is private and exits nonzero on any delivery or
style mismatch. No missing app or authentication failure counts as a pass.

### React apps

`@scitex/sdk/ui/react/app/app-header` exports `AppHeader`. Pass `title`,
`version`, and a React `projectSelector` (plus optional `actions`). The binding
creates the existing TypeScript component and portals children into its slots;
it does not define a second header template or stylesheet. Text updates preserve
the mounted picker. React unmount destroys only the binding-owned row. A host
that already owns a server-declared header should portal into that row instead
of rendering another binding.

## Host boundary and viewport frame

The SDK shell adds no accent stripe at the top of app content, including
`#main-content[data-app-accent]` and `.stx-shell-content`. Accent tokens remain
available for content controls and panel tints; they do not create a second
horizontal line immediately below the global header.

The host owns the outer frame width, centering, and platform backdrop. A leaf
fills its allotted content pane and keeps layout changes inside that pane.
It must not override the host's `.workspace-layout` / `.workspace-three-col`
width, margins, or background. On Hub, `--site-content-max-width` matches app
and global-header widths; surrounding space uses Hub's theme-aware backdrop.
SDK project audits and native hooks enforce ownership of these shell surfaces.

On phones the shell reads the three explicit utility declarations emitted by
`panes={"ai": "unused", "files": "unused", "viewer": "unused"}`. If all three
are unused, the body and module use finite flex space below the naturally sized
host header; there is no app-specific header offset. Otherwise the utility
stack remains reachable by page scrolling. An app keeps its internal scrolling
inside the module frame.

Shell sizing and mobile gestures own only direct utility sidebars, including
the host's Chat/Console and Editor utility wrappers. A nested app Details pane
keeps its own collapse, dimensions and ARIA state. The shell must neither clear
that class on a breakpoint nor restore it from utility preferences.
`tests/browser/shell-frame.spec.ts` exercises real wheel scrolling, varied
header and viewport heights, direct/wrapped utilities and nested sidebar state.
These cases run in the existing `frontend / header-browser` CI job. The two
shell stylesheets and mobile runtime use `app_static` URLs, so changed asset
bytes change the browser URL without manual version strings.

## Read-only page scope

A page may intentionally start at All Projects while the user's shared profile
remembers a project. Pass `viewSelection: {scope: "user", id: null}` to the
picker, or `view_scope="user"` to `scitex_project_picker`, to label that initial
page view. This explicit pair is separate from the remembered scope; loading it
makes no profile write. A user choice supersedes it through the normal provider.
Availability and disabled reasons still come from the host; an unknown or
disabled page project cannot become selected. For a project page, use
`view_scope="project" view_project=authorized_project_id`.

Resolve explicit server-side project views with
`resolve_project(request, provider, explicit=selector, remember=False)` to retain
access checks without changing a global preference during a GET. Apps with
multiple scope modes should handle the picker's change event and navigate their
own view (`navigate=""` disables the default project-only navigation).
