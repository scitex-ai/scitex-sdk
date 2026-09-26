# Changelog

All notable changes to `scitex-sdk`.

## [Unreleased]

### Added
- `scitex_sdk.creator` — the App Creator wizard as a web UI (first
  implementation living in the SDK, not behind the facade): starter
  cards (data entry / dashboard / log viewer / blank), new-app
  scaffolding, validation feedback, and publish / dev-install hooks.
  The engine (scaffold, validate, publish, dev-install) is imported
  from `scitex-app`'s appmaker until the implementation consolidates.
- `scitex-sdk gui {serve,open,status,stop}` console script
  (`scitex_sdk.cli:main`, plus `python -m scitex_sdk`) — the
  ecosystem-standard GUI lifecycle on fixed port `31301`.
- `scitex_sdk.creator.urls` + `manifest.json` (slug `create-app`) for
  generic host mounting, e.g.
  `path("create-app/", include("scitex_sdk.creator.urls"))`.

The versioning here is the **umbrella** release (the facade + the gradually
moving implementation). Each half keeps its own version through the migration
window: `scitex_app.__version__` (scitex-app) and `scitex_ui.__version__`
(scitex-ui). See ADR 0001 (scitex-app) and ADR 0003 (scitex-ui).

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
