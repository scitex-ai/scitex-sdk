---
description: |
  [TOPIC] Mobile panes — one column per screen on phones
  [DETAILS] Declare an app's columns as panes; at <=640px a sticky tab bar switches the single visible pane, swipe moves to the adjacent tab, the active pane is remembered, and `.stx-acc` holds secondary settings.
tags: [scitex-ui-mobile-panes]
---

# Mobile panes

A multi-column web app (Data | Plot | Settings, Files | Editor | Preview) does not fit a
390px screen. Stacking the columns makes the user scroll past whole tools to reach the
one they want; hiding them makes them unreachable. The panes primitive keeps the columns
and shows **one per screen**, with tabs at the top.

| Width | Behaviour |
|-------|-----------|
| > 640px | Panes side by side, as before (CSS grid; column widths from the app) |
| <= 640px | Tab bar at the top, then the active pane's own header, then its content |

On phones:

- the tab bar is sticky, 44px targets, icon plus short label, and scrolls horizontally when there are many panes;
- the active pane fills the height between the site header and the dock
  (`100dvh - --site-header-height - --site-dock-height`; override with `--stx-panes-phone-height`);
- a horizontal swipe moves to the adjacent tab. It never starts inside a horizontal scroller
  (plot-type rail, table, code editor), a text field, or anything marked `data-stx-no-swipe`;
- the active pane is remembered per app in `sessionStorage` (`stx-panes:<app>`).

## Template tag

```django
{% load i18n scitex_panes %}
{% scitex_panes "figrecipe" columns="280px minmax(0,1fr) 320px" %}
  {% scitex_pane "data" label=_("Data") icon="📊" order=1 %}
    <header data-stx-pane-header>…the pane's usual title row…</header>
    …
  {% endscitex_pane %}
  {% scitex_pane "plot" label=_("Plot") icon="📈" order=2 %}…{% endscitex_pane %}
  {% scitex_pane "settings" label=_("Settings") icon="⚙️" order=3 %}…{% endscitex_pane %}
{% endscitex_panes %}
```

`scitex_panes` arguments: the app id (storage namespace), `columns` (desktop
`grid-template-columns`), `active` (initial pane when nothing is remembered), `layout="app"`
(keep the app's own desktop layout, no grid), `css_class`. `scitex_pane` arguments: the pane
id, `label`, `icon` (text or emoji), `order`, `css_class`. The tag loads
`css/app/panes.css` and the module `js/app/panes.js`.

## Plain markup

The tag only writes this; any page can write it directly:

```html
<link rel="stylesheet" href="{% static 'scitex_sdk/ui/css/app/panes.css' %}">
<div data-stx-panes="figrecipe" style="--stx-panes-columns: 280px 1fr 320px">
  <section data-stx-pane="data" data-stx-label="Data" data-stx-icon="📊" data-stx-order="1">…</section>
  <section data-stx-pane="plot" data-stx-label="Plot" data-stx-icon="📈" data-stx-order="2">…</section>
</div>
<script type="module" src="{% static 'scitex_sdk/ui/js/app/panes.js' %}"></script>
```

Panes must be direct children of the root. A child with `data-stx-pane-header` stays pinned at
the top of its pane on phones.

## Switching from code

```js
window.stxPanes.show("plot");               // e.g. after the user picks a plot type
window.stxPanes.show("plot", "figrecipe");  // when a page has several panes roots
document.addEventListener("stx-panes:change", (e) => console.log(e.detail)); // {app, pane, previous}
```

With a bundler: `import { Panes, mountPanes, stxPanes } from "@scitex/sdk/ui/ts/app/panes"`.
`new Panes(root, { app, media, storage })` accepts a media query and storage stand-in, which is
how the tests drive the breakpoint.

## Accordion for secondary settings

Tabs are for the columns. Inside a pane, rarely changed settings go in an accordion:

```html
<details class="stx-acc">
  <summary>Axis</summary>
  <div class="stx-acc__body">…</div>
</details>
```

Do not turn the columns themselves into accordions.

## Demo and tests

- `python examples/04_mobile_panes_demo.py` writes a standalone demo page (`index.html` in the run's session directory).
- `npx vitest run` covers switching, persistence, breakpoint and swipe
  (`tests/scitex_sdk/ui/vitest/panes.test.ts`); `tests/scitex_sdk/ui/templatetags/test_scitex_panes.py` covers the tag.
