# Native section navigation

Use native anchors with the SDK's shared underline styling. These are document
locations, not tab panels: do not set `role="tab"` or `aria-selected` on links,
and do not hide the rest of the page.

```html
<link rel="stylesheet" href=".../scitex_sdk/ui/css/app/content-tabs.css">
<nav data-stx-section-nav aria-label="On this page" class="stx-content-tabs">
  <a class="stx-content-tabs__tab" href="#overview" aria-current="location">Overview</a>
  <a class="stx-content-tabs__tab" href="#details">Details</a>
</nav>
<section id="overview">...</section>
<section id="details"><span id="legacy-details"></span>...</section>
<script type="module" src=".../scitex_sdk/ui/js/app/section-nav.js"></script>
```

Use the host's `app_static` tag for content-addressed resource URLs where available.
The host owns sticky placement and layout. The controller measures the nav's
actual bottom edge and each section's computed `scroll-margin-top`, so native
anchor heading clearance remains current after later geometry updates. Its sticky
top must correctly follow the host header.
Nav/header size changes, viewport resizing, captured scroll events, hash changes
and browser back/forward schedule a single animation-frame update. A short final
section becomes current at the page bottom. Initial hashes and aliases inside a
section resolve to that section's canonical nav link; malformed or unrelated
anchors are ignored. Targets can also use `[data-stx-section]` instead of `section`.

Only `aria-current="location"` is updated on the matching native links. Manual
scrolling never rewrites the URL/history, and native link navigation, keyboard
activation and browser restoration remain browser-owned. `aria-current="page"`
and `aria-selected="true"` receive the identical shared underline where their
respective semantics are appropriate. Without JavaScript, all anchors and content
remain usable.

The TypeScript API exports `SectionNav` and idempotent `mountSectionNavs(root)`.
Call `refresh()` after deliberately changing an existing navigator's links, or
`destroy()` when removing it. The component is also discoverable as `section-nav`
through the existing SDK component registry. Rebuild the shipped browser module
from source, rather than editing generated JavaScript:

```bash
node scripts/build-ui.mjs --only js/app/section-nav.js
```
