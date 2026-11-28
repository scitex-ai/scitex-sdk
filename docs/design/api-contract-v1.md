# SciTeX public API contract v1

**Status: DRAFT for decision (2026-11-28).** Nothing in this document changes a live endpoint.

**Audience:** leaf authors, Hub maintainers, the inventory and contract-test owners, and the operator.

| Part | Contents |
|---|---|
| this file | the spine, what already exists, decisions for the operator, order of work |
| [01-rules.md](api-contract-v1/01-rules.md) | §1 rule registry with stable ids (`API-D/R/V/F/E/A/G/J/I/H/C/T/O`); §2 how a leaf adds an endpoint and what a violation looks like |
| [02-docking.md](api-contract-v1/02-docking.md) | §3 docking (in-process and out-of-process, identity, data, jobs, health, contract versions, one plugin model); §4 `api list` and `GET /api/v1/operations`; §5 three-layer enforcement |
| [03-decisions-taken.md](api-contract-v1/03-decisions-taken.md) | §6 decisions taken without escalation, with rationale and real before → after; §7 rewrite / facade / remove |
| [04-migration.md](api-contract-v1/04-migration.md) | §8 every current endpoint and tool → v1, with owner, breaking, effort, pre-beta; counts |
| [05-hosted-mcp.md](api-contract-v1/05-hosted-mcp.md) | §11 hosted MCP over the internet: endpoint, auth (bearer key, OAuth 2.1), same generic layer, exposure tiers, discovery, migration from `/mcp`, an end-to-end URL + key example |
| [06-public-light.md](api-contract-v1/06-public-light.md) | §12 cost class and exposure ceiling; priority classes (paid > member > public); sponsored public tier as config; promotion budget, alerts, degradation |

**Inputs, read on 2026-11-28:**

- **scitex-sdk** `origin/develop` `c4e35b4`. PR #175 added the operation layer (`api_ops`,
  `api_exec`, `api_serve`, `api_mcp`), released in 0.3.26.
- **scitex-hub** `origin/develop` `f2cbe84`:
  - `config/urls.py`, `config/urls_api.py`;
  - `accounts_app/services/api_caller.py`;
  - `apps_app/services/app_loader.py`;
  - `public_app/urls/api.py`, `platform_app/urls/api.py`.
- **scitex-dataset** `origin/develop`: `_rest/__init__.py`, the pilot.
- **scitex-dev** `origin/develop`: §2 MCP naming (`_mcp_tool_naming.py`) and the §1d CLI verb
  catalogue.
- **The 2026-11-27 API audit** (scitex-hub #1245).

---

## 0. The spine: an endpoint exists only if the SDK generated it

> Operator, 2026-11-28: "api points should be normalized by enforcing api points using scitex-sdk";
> "sdk and leaf packages should provide api points in a docking manner to scitex-hub".

There is exactly one way a public SciTeX endpoint or remote MCP tool can exist:

1. **Declare.** A package declares **operations** with `scitex_sdk.app.api_ops.ApiOperation`, each
   a verb on a plural resource of that package, and bundles them with `build_plugin(...)`.
2. **Advertise.** The package advertises the plugin through the `scitex.apis` entry point. Its
   wheel also ships the inert descriptor `scitex_api.json`.
3. **Derive.** The SDK derives everything else from that one declaration: URL, method and success
   status, scope, MCP tool name and input schema, OpenAPI operation, error envelope, pagination,
   idempotency, request id, and the `api list` row. A leaf writes none of these by hand, so it
   cannot spell them differently.
4. **Dock.** A host, either the Hub or the leaf's own standalone server, docks admitted plugins with
   `scitex_sdk.app.api_serve.api_urlpatterns()`. The host supplies identity, scopes, rate limits,
   metering and idempotency storage through generic hooks, and contains no leaf-specific code.
5. **Enforce at three layers:**
   - **declaration:** the constructor raises with a rule id;
   - **CI:** the SDK contract test in every leaf and the Hub, plus the `scitex-dev` audit;
   - **runtime:** the Hub mounts only admitted, conforming plugins, refuses the rest loudly, and
     freezes legacy routes on a shrinking allowlist.

Hub-native platform resources (users, tokens, projects, files, orgs, billing, events) follow the
same rule. The Hub declares them as an ordinary plugin with package slug `hub`, served by the same
machinery, so there is no second grammar for platform endpoints.

### 0.1 What already exists (verified on `develop`, 2026-11-28)

| Piece | Where | State |
|---|---|---|
| Operation layer: URL, method, status, scope, MCP name, operation id all derived | sdk `api_ops.py` | shipped 0.3.26 |
| Declaration-time refusal (`ApiPluginContractError`) | sdk `api_ops.py`, `api_plugin.py` | shipped, **no rule ids yet** |
| One execution core for REST and MCP (scope, params, project authz, envelope) | sdk `api_exec.py` | shipped |
| Generic `/api/v1/<package>/` serving: problem+json, `X-Request-Id`, `Idempotency-Key`, 404/405 problems | sdk `api_serve.py` | shipped |
| MCP tools generated 1:1 from operations | sdk `api_mcp.py` | shipped |
| Source auditor `PS-SDK-WEB`, dispatched by `scitex-dev ecosystem audit-project` | sdk `_api_source.py`, `_api_contract.py` | shipped |
| Inert descriptor `scitex_api.json` in the wheel | sdk `api_build.py`, `api_mount.py` | shipped |
| Hub mounts every trusted plugin with one line and refuses off-grammar plugins | hub `config/urls.py`, sdk `api_serve.admitted_plugins` | shipped |
| Hub caller: `Authorization: Bearer scitex_…`; a bad bearer gets 401 | hub `accounts_app/services/api_caller.py` | shipped |
| Hub test: no Hub source names a leaf API | hub `tests/config/test_api_v1_generic_mount.py` | shipped |
| **Pilot:** scitex-dataset declares 9 operations, served in-process at `/api/v1/dataset/…`, MCP `dataset_*` | dataset `_rest/__init__.py`; hub `test_dataset_mount.py` | shipped |

Specified here and not built yet:

- rule ids in errors; a contract version; `public` operations; `Location` on 201; a fixed Job
  schema;
- the legacy-route freeze; the shared contract test;
- `api list` and `GET /api/v1/operations`; out-of-process docking; the `hub` dock;
- merged OpenAPI; remote MCP at `/api/v1/mcp`; rate-limit and deprecation headers.

### 0.2 v1 grammar at a glance

```
/api/v1/<package>/<resource>[/{<resource_singular>_id}][/<action>]      package-generated
/api/v1/operations      GET   live list of every docked operation (composed from leaf lists)
/api/v1/openapi.json    GET   merged OpenAPI 3.1
/api/v1/mcp             MCP   remote MCP: derived tools of admitted docks, scope-filtered
/api/v1/health          GET   platform liveness
/api/v1/hub/...               Hub platform resources, same grammar (docks, projects, tokens, files, ...)

list GET 200 · get GET 200 · create POST 201+Location · update PATCH 200 · delete DELETE 204
action POST 200 | 202 {"job": Job}       project-scoped: ?project=owner/slug (or in the body)
scope  <package>:<resource>:<read|write>  MCP  <package>_<resource>_<verb>  opId <package>.<resource>.<verb>
auth   Authorization: Bearer <token>      errors application/problem+json {type,title,status,detail,code,request_id,retryable,errors}
lists  ?limit=&cursor= → {data, has_more, next_cursor}   writes need Idempotency-Key   every response X-Request-Id
         and SciTeX-Priority-Class: paid|member|public
declare compute_cost light|standard|heavy + exposure public_eligible|member|privileged   (who is sponsored = host config)
```

Hosted MCP is the same operations over MCP streamable HTTP at `/api/v1/mcp`
([05](api-contract-v1/05-hosted-mcp.md)). An agent that knows the URL and a key can list the tools
its scopes grant and call them, and results and errors are the REST bodies.

---

## 9. Decisions for the operator

Answer by number. The first option in each item is the recommendation.

1. **MCP tool name order.**
   - Current state: the SDK derives `<package>_<resource>_<verb>` (`dataset_datasets_list`,
     `clew_claims_verify`), and the dataset pilot ships it. scitex-dev §2, which you confirmed, says
     `<pkg>_<verb>_<noun>` (`clew_verify_claim`).
   - **(a) Recommended:** keep the SDK order for every SDK-derived (public) tool, and amend §2 so the
     auditor checks derived tools by their operation metadata (API-T001). §2 already accepts the
     noun-group form (`dev_ecosystem_list`). This order groups tools by resource and mirrors CLI
     `<noun> <verb>` groups.
   - (b) Change the SDK to `<package>_<verb>_<resource>` (`dataset_list_datasets`). This renames
     the 9 dataset tools now (S), before anything depends on them.
2. **Canonical project id.**
   - **(a) Recommended:** the public id is the handle `owner/slug`.
     - It is already the SDK's `project` parameter, written `owner~slug` inside a path segment.
     - Responses also carry an immutable `uid` (`prj_…`).
     - After a rename, an alias table keeps old handles resolving for the deprecation window.
   - (b) An opaque `prj_…` id is canonical everywhere, and the handle is accepted as an alias. This
     is more stable, but humans and agents must look ids up first, and the shipped dataset contract
     changes.
3. **Deprecation window and v1 freeze.**
   - **(a) Recommended:**
     - v1 is frozen (additive-only) from beta launch.
     - Legacy routes get `Deprecation` now and `Sunset` = beta + 6 months.
     - `/api/v1/scholar/search/`, which has live users, stays as a frozen alias for at least 12 months.
   - (b) A "v1-beta" period until GA, with breaking changes allowed on 30 days' notice.
   - (c) A 3-month legacy sunset.
4. **Third-party (user-published) apps that expose APIs.**
   - **(a) Recommended:** out-of-process only (API-D009), admitted by the existing AppsModule
     approval with a pinned commit. They follow the same grammar, scopes and metering as
     first-party apps.
   - (b) No third-party APIs at beta; UI facet only.
   - (c) In-process after review.
5. **Path prefix for Hub platform resources.**
   - **(a) Recommended:** `/api/v1/hub/<resource>`. The Hub is a package like any other, so there is
     no grammar exception.
   - (b) Top-level `/api/v1/projects`, `/api/v1/tokens`. URLs are shorter, but this adds special
     cases in the SDK, in scopes and in MCP names.
6. **Hosted MCP endpoint path.**
   - **(a) Recommended:** `https://scitex.ai/api/v1/mcp`. It sits behind the same gateway, rate
     limits and nginx rules as REST, and is versioned with the contract that its tools derive from.
     The OAuth protected-resource URL is unambiguous. Today's `/mcp` stays operator-only until it
     is retired.
   - (b) `https://scitex.ai/mcp`. Shorter, and the current location, but unversioned, outside the
     `/api/v1` gateway, and it collides with the operator umbrella during migration.
   - (c) A separate host, `https://mcp.scitex.ai/`.
7. **Hosted MCP tool set and public listing at beta.**
   - **(a) Recommended:** serve every SDK-derived operation of admitted docks, filtered by token
     scope and tier (public / member / privileged; shell, exec and RPC are never served). List the
     server on the official MCP registry and lobehub **after** the DEV acceptance run, together
     with the product A2A card.
   - (b) A lifecycle-only subset (about 25 operations), widened one at a time.
   - (c) List on registries at beta launch, before the acceptance run.
8. **OAuth client registration for agents and MCP clients.**
   - **(a) Recommended:** Dynamic Client Registration (RFC 7591) for public clients only, with:
     - PKCE required;
     - scopes capped to read plus explicitly consented writes;
     - registration rate-limited;
     - unused clients expired after 90 days.

     Claude and ChatGPT connectors need DCR.
   - (b) Pre-registered clients only.
9. **Monthly internal budget for sponsored public compute** (`public_compute` kind on the #1256
   promotion account).
   - **(a) Recommended:** **USD 40/month**, revisited monthly against funnel data.
     - Alerts fire at 50/80/100 %.
     - A global backstop sits at 1.25 × (download sponsorship + compute budgets).
     - The system runs in shadow mode for the first cycle.
   - (b) USD 30/month.
   - (c) USD 50/month.
   - (d) No sponsored compute; discovery and search only.
10. **Limits for the light class and the public profiles** ([06 §12.4](api-contract-v1/06-public-light.md)).
    - **(a) Recommended:**

      | Profile | CPU | Memory | Wall | Input | Output |
      |---|---|---|---|---|---|
      | light | 1 CPU-s | 256 MiB | 5 s | — | 1 MiB |
      | stats-inline | 2 CPU-s | 512 MiB | 10 s | 100 k values | — |
      | stats-bootstrap | — | — | 30 s | 100 k values, ≤ 10 k resamples | — |
      | figure-inline | — | 1 GiB | 20 s | 100 k points, 12 panels | 5 MB |
      | pdf-compile-public | 2 cores | 2 GiB | 120 s | 20 MB | 50 pages |

      PDF compile also runs with no network, no shell-escape, an out-of-process sandbox and a
      2-slot pool.
    - Priority shares: paid ≥ 60 % reserved, public ≤ 20 % per pool.
    - (b) Half these limits.
    - (c) Light only (1 CPU-s / 5 s) for every public operation, and no public PDF compile.
11. **Initial public (sponsored) operation list for the first phase.** This is config, not contract,
    and can be narrowed later.
    - **(a) Recommended**, broad as you asked:
      - dataset catalogue list/get and curated list/get;
      - scholar papers/sources list;
      - clew hash verify;
      - published Live Paper get;
      - stats tests list/get/recommend/run, plus descriptives, effect sizes, power, corrections and
        bootstrap CIs on inline data;
      - figrecipe figure create on inline data;
      - writer manuscript compile, **key required** (any key, no anonymous compile).
    - (b) (a) without PDF compile.
    - (c) Search and describe only (dataset, scholar, clew hash, Live Paper get).

Everything else is decided in [03-decisions-taken.md](api-contract-v1/03-decisions-taken.md), with
its rationale.

---

## 10. Order of work (critical path to beta)

Item numbers refer to [04-migration.md](api-contract-v1/04-migration.md).

1. **SDK basics.** E1–E5 and E7 (S each). The rule ids are published here first, so the inventory
   tags violations with them.
2. **Lists and tests.** E8 (`api list` / `GET /api/v1/operations`, inventory owner), E6 (contract
   test on the same inventory module) and E13 (Hub allowlist test).
3. **Hub.**
   - E14: the `hub` dock (projects, tokens, uploads/files, users, docks, events).
   - E12: rate-limit and deprecation headers.
   - Security removals: #32, #47–#49, #59–#69.
4. **Leaves, in parallel.** clew (#78–#88), writer (#91–#93), live-paper (#117–#118), stats
   (#59–#65, #110, #116), scholar (#57, #99). The dataset pilot is done.
5. **Discovery and MCP.** E9 (OpenAPI), E10 + E19 (hosted MCP), then the umbrella (#133–#134).
6. **Public tier.** E16 (exposure ceiling, cost measurement, priority, public-tier config), E17
   (`public_compute` sponsorship in shadow mode), E18 (sandboxed public compile pool).
7. **Out-of-process.** E11 (out-of-process docking), with hpc (#70–#72) as its first user.
8. **Acceptance on DEV.** An external agent completes the research lifecycle over `/api/v1/mcp`
   with a scoped token, recorded with screenshots and logs (paper-scitex-clew QA).
