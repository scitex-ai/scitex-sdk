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
