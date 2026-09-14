# scitex-sdk

One project for the SciTeX **app contract** + **UI shell** — so the two are
named, versioned, and released as a single unit.

```
scitex_sdk.app   ->  the app contract   (from scitex-app)
scitex_sdk.ui    ->  the UI shell       (from scitex-ui)
```

## Step 1: thin facade

`scitex_sdk.app` re-exports `scitex_app`'s documented public surface **by
identity** (the same objects), and `scitex_sdk.ui` re-exports `scitex_ui`'s.
That makes a consumer's import rewrite mechanical and behavior-neutral:

```python
# before
from scitex_app import get_files
# after
from scitex_sdk.app import get_files   # identical object
```

`tests/test_facade_identity.py` asserts every re-export is the *same object*
as the original — a copy or reimplementation fails the suite.

## Roadmap

1. **Facade (this)** — re-export, identity tests, release. Consumers can start
   rewriting imports against it.
2. **Gradual implementation move** — code moves from `scitex_app` /
   `scitex_ui` into `scitex_sdk.app` / `scitex_sdk.ui`; the original
   distributions stay as thin compat shims until every consumer has migrated.
3. **Shim removal** — only after all consumers (hub, figrecipe, writer,
   scholar, cards, agent-container GUI) are on `scitex_sdk`.

The static/TS/CSS assets live in `scitex_ui` today (Django's
AppDirectoriesFinder resolves them by the `scitex_ui` app label); they move
with the implementation step, not the facade.
