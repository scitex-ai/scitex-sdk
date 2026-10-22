# SDK Python API map

Three lazy facades (identity re-exports, never copies):

- `scitex_sdk.app` — App contract: scaffold, validation, embed
  (`serve_gui` / `run_standalone`), project context, file backends.
- `scitex_sdk.ui` — UI shell: component registry, project scope,
  mount helpers, Django views/middleware/context processors.
- `scitex_sdk.project` — the project primitive (same objects as
  `scitex_dev.project`, by identity).

Rule of thumb: domain GUI code lives in the leaf's `_django` package and
imports App/UI from `scitex_sdk`; Hub provides authenticated capabilities
and generic mounts. Introspect the live tree with
`scitex-sdk list-python-apis --json`.

Full API detail lives in the scitex-app / scitex-ui skills
(`03_python-api.md` in each).
