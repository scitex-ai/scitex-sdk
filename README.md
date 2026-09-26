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

## App Creator wizard

`scitex_sdk.creator` is the first implementation that lives in the SDK
rather than behind the facade (new code, not moved code): the appmaker
scaffolding wizard as a web UI, served by the SDK for both standalone
use and host mounting.

```bash
scitex-sdk gui serve    # wizard at http://127.0.0.1:31301/ (blocking)
scitex-sdk gui open     # auto-serve (if needed) + open a browser
scitex-sdk gui status   # running / not-running (+ --json)
scitex-sdk gui stop --yes
```

The wizard covers: new app from starter (label / description /
starter card: data entry, dashboard, log viewer, blank), inline
validation feedback, `api/validate-app` on an existing app dir, and
publish / dev-install hooks against a SciTeX Cloud server. The engine
(scaffold, validate, publish, dev-install) is still imported from
`scitex-app`'s appmaker and consolidates here gradually.

Hosts mount the same Django app generically:

```python
path("create-app/", include("scitex_sdk.creator.urls"))
```

(`manifest.json` slug `create-app`, port `31301` — the first 3130X
overflow slot; 3129X is full per scitex-dev's reserved-port scheme.)
