# API contract v1: 3. Docking, 4. Listing, 5. Enforcement

Part of [api-contract-v1.md](../api-contract-v1.md).

## 3. Docking

A **dock** is one distribution's set of operations. A host admits it and serves it at
`/api/v1/<package>/`. Docking is the only way a package provides API points to the Hub.

### 3.1 Lifecycle

```
declare           advertise              admit (host startup)            serve
ApiOperation  ->  entry point       ->   discover; validate grammar  ->  REST    /api/v1/<pkg>/...
build_plugin      scitex.apis            (API-*), contract major         MCP     /api/v1/mcp (scoped)
                  + scitex_api.json      (API-D003), trust/approval      OpenAPI /api/v1/openapi.json
                                                                         list    /api/v1/operations
```

- **Dock.** For in-process, install the distribution in the Hub environment. For out-of-process,
  configure its service URL (§3.2). Then admit it:
  - first-party: by `SCITEX_API_TRUSTED_DISTRIBUTIONS` (today `("scitex-*", "figrecipe")`);
  - third-party: by an approved `AppsModule` (§3.7).
- **Undock.** Uninstall it, or remove it from the trusted set or `SCITEX_API_DOCKS`. Its paths then
  answer a 404 problem and its tools disappear from `/api/v1/mcp`. Nothing else in the Hub changes.
- **Discovery** reads entry points and inert descriptors. It never imports leaf code before
  admission (API-D006, shipped in `api_mount`).
- **Generic host hooks.** The Hub applies identity, scopes, CSRF, rate limits, idempotency, metering
  and request ids through the SDK host hooks: `SCITEX_API_CALLER`, `SCITEX_API_RATE_LIMITER`,
  `SCITEX_API_METER` and `SCITEX_API_IDEMPOTENCY_STORE`, all shipped. A handler sees an `ApiCall`
  and never a token.

### 3.2 Two modes from one declaration

| | In-process | Out-of-process |
|---|---|---|
| Handler runs | in the Hub worker (`api_exec.execute` imports `module:function`) | in the leaf's own service |
| Hub mounts | `operation_view(plugin, route)` (shipped) | the same `operation_view`, with handler = SDK proxy `api_proxy.forward` (**new**) |
| Declaration source | entry point in the Hub env | the service's `GET /_dock/descriptor` (inert JSON, same parser), which must equal the pinned wheel's `scitex_api.json` |
| Auth, scope, rate, idempotency, meter | Hub hooks | Hub hooks, **before** forwarding; the service re-checks scope from the internal token |
| Leaf server | none | `scitex-sdk api serve <distribution> --bind …`, a generic server built by `api_serve` from the same plugin (**new**) |
| Public URL, MCP name, scope, OpenAPI | derived from the declaration | identical, derived from the same declaration |

Switching mode is Hub configuration only:

```python
# Hub settings: no entry → in-process (if installed); an entry → out-of-process
SCITEX_API_DOCKS = {
    "hpc": {"mode": "remote", "url": "http://scitex-hpc.internal:8710",
            "distribution": "scitex-hpc"},
}
```

Nothing public is configured here, so the public contract cannot change. The contract test (§5)
runs one suite against both modes.

### 3.3 Identity across the boundary (out-of-process)

- The Hub authenticates the user's bearer or session. The raw credential never leaves the Hub
  (API-D009).
- The Hub forwards a **signed internal token** on the internal hop as `Authorization: Bearer`:
  - format: a JWS signed with the Hub's Ed25519 dock key, `typ=scitex-dock+jwt`;
  - audience and lifetime: `aud=<package>`, `exp` = 60 s;
  - claims: `sub` (opaque user id), `scopes` (the caller's grant), `token_id`, `project`
    (`{id, handle, can_write}`, resolved by the Hub's `project_access`), `request_id` and `payer`.
- On the service, `SCITEX_API_CALLER` is the SDK's `dock_token_caller`. It verifies the signature
  against the Hub's published dock key, plus `aud` and `exp`, and builds `ApiCaller` from the
  claims. It accepts nothing else.
- Project files: an out-of-process leaf gets no Hub filesystem path. It reads and writes through
  the same `scitex_sdk.host` capability objects an in-process handler uses, backed by the Hub's
  internal files capability. Handlers are therefore identical in both modes.

### 3.4 Leaf-owned data

- **In-process.** The leaf ships a Django app (label `scitex_<pkg>`) with its own migrations, in
  the same distribution. Its tables are prefixed by the label, and the Hub runs `migrate` for docked
  apps during deploy.
  - A leaf never writes Hub tables. It reaches users, projects, storage and spend only through
    `scitex_sdk.host` capabilities.
  - Undock leaves the tables in place. Dropping them is an explicit, audited step through
    scitex-storage.
- **Out-of-process.** The service owns its database. The Hub keeps only the dock record.
- **Retired.** The generic `/platform/api/data/<app>/<schema>/` datastore is retired. A leaf that
  needs tables declares them as above.

### 3.5 Long-running work, health and readiness

- **Jobs** follow API-J001 in both modes. The job record lives with the leaf (`<package>/jobs`).
  The Hub's meter and spend hooks see the job id in the 202 response.
- **Health, in-process.** The plugin may declare `health="module:function"`, which the SDK calls
  with a 2 s budget. Without one, an admitted dock counts as healthy.
- **Health, out-of-process.** The SDK server exposes `GET /_dock/health` (liveness) and
  `GET /_dock/ready` (dependencies ready).
- **Hub view.** The Hub aggregates both in `GET /api/v1/hub/docks` (`hub_docks_list`): package,
  distribution, version, contract, mode, state (`docked | refused | unhealthy`), and the refusal
  rule id and message. `GET /api/v1/health` is the platform liveness summary.

### 3.6 Contract versioning and refusal

- The SDK exports `CONTRACT_MAJOR = 1`. A plugin declares `contract="1"`: the default during SDK
  0.3.x, required from 0.4. A host declares the set it supports (Hub: `{1}`).
- The Hub **refuses** a dock with an unsupported major, an off-grammar declaration, or a remote
  descriptor that differs from the pinned wheel. A refusal:
  1. logs at ERROR with the rule id, for example
     `[API-D003] scitex-foo contract 2 not supported (host supports 1)`;
  2. is recorded in `api_serve.REFUSED` and shown as `refused` in `hub/docks`;
  3. makes `/api/v1/health` report `degraded`;
  4. **fails the Hub's CI and deploy smoke test** when the refused distribution is in the trusted
     set, so a refusal is never a silently missing endpoint.

  The rest of the Hub keeps serving: one bad leaf cannot take the platform down.
- The plugin's `api_version` (`"1"` in dataset) is the package's own operation release line. It
  is reported in `hub/docks` and in OpenAPI `x-scitex-api-version`. The `v1` in the path is the
  contract major, not a package version.

### 3.7 One plugin model for UI and API

The Hub has four discovery paths today:

| Today | Purpose | Admission |
|---|---|---|
| `scitex.apps` (sdk `plugins.py`, Hub `plugin_urlpatterns`) | first-party UI apps at `/apps/<name>/` | installed in the Hub env |
| `scitex_hub.apps` + `scitex_hub.app_config` (Hub `app_loader.py`) | user-published apps at `/apps/u/<module>/` | `AppsModule` approved by Gitea PR merge, commit pinned |
| `scitex.apis` | API operations at `/api/v1/<package>/` | `SCITEX_API_TRUSTED_DISTRIBUTIONS` |
| Hub-native views | platform | hard-wired |

In v1 there is **one dock record per distribution, with two optional facets**:

- **`ui` facet:** the `scitex.apps` entry point and manifest (tile, mount policy, i18n), unchanged.
- **`api` facet:** the `scitex.apis` entry point and `scitex_api.json`, as specified here.
- **One admission covers both facets.**
  - First-party: by the trusted pattern.
  - Third-party: by an approved `AppsModule`. The `ApiAdmission.review_ref` becomes
    `apps-module:<id>@<pinned_commit>`, an existing field.
  - The submission flow (`/api/apps/submit/`, Gitea PR, `pin_commit`) is kept and becomes the
    admission source for both facets.
- **`scitex_hub.apps` and `scitex_hub.app_config`** fold into `scitex.apps`. The
  `/apps/u/<module>/` UI location stays.
- **Hub-native platform resources** become the `hub` dock: a plugin in Hub source, passed as
  `api_urlpatterns(refs=[hub_ref, …])`. Explicit refs are already supported. It gets the same
  grammar, the same `api list` and the same contract test.
- **Third-party API facets** dock out-of-process only (decision 4).

### 3.8 Mode per current leaf (recommendation)

| Package | Mode | Why |
|---|---|---|
| hub | in-process | it is the host |
| dataset | **in-process: the pilot, done** | light handlers; heavy fetch runs as a job; mounted at `/api/v1/dataset/…` today |
| clew | in-process | the Hub already provisions the per-project Clew store; handlers do file and hash work |
| writer | in-process | the UI is already docked in-process; compile is a job in the existing compile container |
| scholar | in-process | the UI is docked in-process; upstream search is I/O-bound, rate class `search` |
| stats | in-process | stateless light calls; reports run as jobs |
| figrecipe | in-process | the UI is docked in-process; renders run as jobs |
| live-paper | in-process | the UI is docked in-process; publish is a job |
| **hpc** | **out-of-process: the first candidate** | holds cluster SSH credentials and host config that do not belong in the Hub process; long jobs; a separate trust boundary by nature |
| third-party apps | out-of-process | untrusted code |

---

## 4. Listing: `api list`, composed from the leaves

Operator-confirmed layout:

- Each leaf exposes its own SDK-provided `api list`.
- The global listing is composed from the leaf lists. There is no separate registry.
- One SDK aggregation function has three front ends.

```bash
scitex-dataset api list            # one leaf: operation id, method, path, scope, MCP tool, public, async
scitex-dataset api list --json     # the same rows, machine-readable (the inventory row schema)
scitex-dataset api list --errors   # the package's error-code registry (API-E002)
scitex api list                    # umbrella (primary): every installed leaf, composed
```

| Front end | Answers | Composition |
|---|---|---|
| `scitex api list` (umbrella, **primary**) | what is installed here | aggregation over installed `scitex.apis` declarations (inert descriptors, no leaf import) |
| `GET /api/v1/operations` (Hub, live) and `GET /api/v1/openapi.json` | what is docked on that server | the same aggregation over **admitted** docks; rows add `mode` and `state`. Grammar-exempt reserved path (API-R006). It is paginated like any list, public, and filterable by `package` |
| `scitex-dev ecosystem audit-project … --rule PS-SDK-API` (CI) | what violates the contract | the same rows, tagged with API-* rule ids |

- **Owner.** The inventory work in scitex-sdk implements the subcommand and the aggregation
  function (`scitex-sdk api inventory`; snapshot under
  `paper-scitex-clew/GITIGNORED/api-inventory-20261128/`). This document fixes the contract only and
  does not duplicate the implementation.
- **Mounting.** The SDK's CLI helpers (`scitex_sdk.app._cli`) mount the subcommand into a package's
  CLI. A package writes no code beyond its plugin, and API-D008 checks that the subcommand is there.
- **One row source.** Rows come from the same `operations(plugin)` used for docking, MCP generation
  and the contract test, so the list, the served API and the enforcement cannot drift.
  `scitex_sdk.testing.api_contract` imports the same module.
- **Hub scan.** The Hub inventory also scans the Hub URLconf for routes that did **not** come from a
  plugin and tags them (API-D001/D004/E003/A001 …). That output is the input to the legacy
  allowlist and to the migration table.

---

## 5. Enforcement in three deterministic layers

| Layer | Mechanism | Fails on | Owner |
|---|---|---|---|
| **Declaration** | `ApiOperation.__post_init__`, `build_plugin` and the `ApiPlugin` constructors raise `ApiPluginContractError(rule=…)` | every D-layer rule | scitex-sdk |
| **CI: leaf** | `scitex_sdk.testing.api_contract`, enabled with one line in the leaf's pytest config (details below) | C-layer rules | sdk ships it; each leaf runs it |
| **CI: audit** | `scitex-dev ecosystem audit-project <pkg> --rule PS-SDK-API`, which extends the shipped `PS-SDK-WEB`. It is source-only and reports API-* ids, and scitex-dev §2 delegates derived tools to API-T001 (decision 1). | same rules, without running code | sdk rule, dev dispatch |
| **CI: Hub** | `tests/config/test_api_surface.py`, built on the shared inventory (details below) | API-D001, D003, D004, O002 | scitex-hub |
| **Runtime** | the Hub refuses or answers a problem (details below) | R-layer rules | sdk + Hub |

**CI, leaf.** `check_plugin(PLUGIN)` plus `run_contract_suite(PLUGIN, modes=("in-process", "remote"))`
boot the plugin on the SDK standalone host and call every operation:

- with no credential: expects 401 problem, or 200 when the operation is `public`;
- with the wrong scope: expects 403;
- with a bad id: expects a 404 problem;
- with the wrong method: expects 405;
- as a write without `Idempotency-Key`: expects 400.

The same suite also:

- validates the OpenAPI document (API-O002);
- checks that the MCP list equals the operation list (API-T002);
- checks that `api list` is present (API-D008);
- diffs the declaration against the last released `scitex_api.json` (API-C001).

**CI, Hub.** `test_api_surface.py` checks that every route under `/api/` is either
plugin-generated or on `config/api_legacy_allowlist.txt`. The allowlist holds today's inventory,
and entries may only be removed. The test also checks that no trusted dock is refused and that the
merged OpenAPI validates. The shipped test "no Hub source names a leaf API" stays.

**Runtime.**

- `admitted_plugins` refuses off-grammar plugins (shipped) and unsupported contracts (new).
- An unmatched `/api/v1/*` path answers a 404 problem (shipped).
- Remote MCP lists only admitted operations (API-T004).
- Legacy routes carry `Deprecation` and `Sunset` (API-H003).

A document is not enforcement. The registry in [01-rules](01-rules.md) is the reference, and each
row names its check.
