---
description: [the three lazy facades and import rules] See SKILL.md workflow; component detail in scitex-app / scitex-ui skills.
tags: [scitex-sdk]
---

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


## Bundled skill catalog

```python
from scitex_sdk import list_bundled_skills

catalog = list_bundled_skills()
assert set(catalog) == {"scitex-sdk", "scitex-app", "scitex-ui"}
```

This returns sorted relative Markdown IDs, without `.md` or the `SKILL.md`
index, directly from package resources. It reads no user skill installation,
workspace, HOME configuration or global provider registry, and returns no
filesystem paths. It does not install anything. App/UI IDs match the existing
`scitex-sdk app dev skills list --json` / `ui dev skills list --json` and MCP
skill-list operations. The root `skills list --json` discovery output also
contains the SDK's index; the bundled catalog deliberately excludes that index.

The same catalog has a declared read-only `skills` Web route. A host must
explicitly admit it; declaring the entry point does not mount or enable a URL.
