# Shared filter fields

The SDK owns filter chrome: a leading filter SVG, search input, and subdued
keyboard badge. Apps supply the subject and matching behavior, rather than
copying markup, keyboard handlers, or component styles.

For a Django-mounted app:

```django
{% load scitex_static %}
<link rel="stylesheet" href="{% app_static 'scitex_sdk/ui/css/app/filter-field.css' %}">
<div data-stx-filter-field data-filter-subject="agents" data-filter-id="agents-filter"></div>
<script type="module" src="{% app_static 'scitex_sdk/ui/js/app/filter-field.js' %}"></script>
```

The module mounts immediately and at DOM ready, idempotently. Load it before
an app module that queries its input. For dynamically inserted content, import
`mountFilterFields` from `@scitex/sdk/ui/app/filter-field` and pass the inserted
root. Call the returned instance's `destroy()` when removing a managed view.

The input placeholder is `Filter agents with keywords`. Change
`data-filter-subject` for another collection; `data-filter-id` is optional.
Listen for the input's normal `input` event to update the app's results.
The SDK does not choose a matching algorithm or send filter requests.

The badge says `Ctrl+K` while unfocused and `Esc` while focused. Ctrl/Command+K
focuses and selects the current visible filter; otherwise it picks the first
visible one. Hidden panes cannot claim it. Escape clears the input, emits an
input event, and blurs. Mouse focus/blur updates the same hint. Composition
input is not intercepted. Colors use shared semantic tokens in both themes;
the keyboard badge is deliberately subdued.

The ownership audit and edit hooks use scitex-dev's existing provider SPI;
filter UI belongs to the SDK just as headers do. Leaf CSS may size the outer
layout wrapper but must not override `.stx-filter-field` or its children.
Use an empty mount instead of handwritten filter icon/input/keyboard markup.

Run `npm run test:headers` after installing Chromium to test the shipped filter
bundle alongside header contracts. The browser checks exercise both themes,
desktop and phone widths, keyboard and mouse focus, Escape's input event,
geometry, remounting, and shortcut cleanup.
