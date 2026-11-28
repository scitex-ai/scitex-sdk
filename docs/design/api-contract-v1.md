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
```

---

## 9. Decisions for the operator

Answer by number. The first option in each item is the recommendation.

1. **MCP tool name order.** The SDK derives `<package>_<resource>_<verb>` (`dataset_datasets_list`,
   `clew_claims_verify`), and the dataset pilot already ships it. scitex-dev §2 (operator-confirmed)
   says `<pkg>_<verb>_<noun>` (`clew_verify_claim`).
   - **(a) Recommended:** keep the SDK order for every SDK-derived (public) tool. Amend §2 so the
     auditor checks derived tools by their operation metadata (API-T001); §2 already accepts the
     noun-group form (`dev_ecosystem_list`). This order groups tools by resource and mirrors CLI
     `<noun> <verb>` groups.
   - (b) Change the SDK to `<package>_<verb>_<resource>` (`dataset_list_datasets`). This means
     renaming the 9 dataset tools now (S), before anything depends on them.
2. **Canonical project id.**
   - **(a) Recommended:** the public id is the handle `owner/slug`. It is already shipped as the
     SDK's `project` parameter, and is written `owner~slug` inside a path segment. Responses also
     carry an immutable `uid` (`prj_…`). Renames keep an alias table, so old handles still resolve
     for the deprecation window.
   - (b) Opaque `prj_…` as the canonical id everywhere, with the handle accepted as an alias. It is
     more stable, but humans and agents must look ids up first, and the shipped dataset contract
     changes.
3. **Anonymous (public) operations at beta.**
   - **(a) Recommended:** these operations, all in the `anonymous` rate class; everything else
     needs a token:
     - `GET /api/v1/operations` and `openapi.json`;
     - `scholar_papers_list`, `scholar_sources_list`;
     - `dataset_datasets_list/get`, `dataset_curated_datasets_list/get`;
     - `clew_hashes_get` (verify a published hash);
     - `live_paper_papers_get` for published papers.
   - (b) Token required for everything except discovery, with a free tier.
   - (c) (a) plus `stats_tests_recommend`.
4. **Deprecation window and v1 freeze.**
   - **(a) Recommended:** v1 is frozen (additive-only) from the beta launch. Legacy routes get
     `Deprecation` now and `Sunset` = beta launch + 6 months. `/api/v1/scholar/search/`, which has
     live users, stays as a frozen alias for at least 12 months.
   - (b) A "v1-beta" period until GA, in which breaking changes are allowed with 30 days' notice.
   - (c) A 3-month legacy sunset.
5. **Third-party (user-published) apps that expose APIs.**
   - **(a) Recommended:** allowed only out-of-process (API-D009), admitted by the existing
     AppsModule approval with a pinned commit. They get the same grammar, scopes and metering.
   - (b) No third-party APIs at beta (UI facet only).
   - (c) In-process after review.
6. **What remote MCP (`/api/v1/mcp`) serves at beta.**
   - **(a) Recommended:** every SDK-derived operation of admitted docks, filtered by token scope.
     Admission is the allowlist, and hand-written tools are never remote.
   - (b) Only a lifecycle subset (about 25 operations), widened one at a time.
7. **Path prefix for Hub platform resources.**
   - **(a) Recommended:** `/api/v1/hub/<resource>` (`/api/v1/hub/projects`). The Hub is a package
     like any other: no grammar exception and no name collisions with leaves.
   - (b) Top-level `/api/v1/projects`, `/api/v1/tokens` with reserved names. The URLs are shorter,
     but this is a special case in the SDK, in scopes (`projects:read` vs `hub:projects:read`) and
     in MCP names.
8. **OAuth client registration for agents and MCP clients.**
   - **(a) Recommended:** allow Dynamic Client Registration (RFC 7591) for public clients only:
     PKCE required, scopes capped to read plus explicitly consented writes, registration
     rate-limited, unused clients expired after 90 days. Many MCP clients (Claude and ChatGPT
     connectors) need DCR.
   - (b) Pre-registered clients only, with a manual allowlist.

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
5. **Discovery and MCP.** E9 (OpenAPI), E10 (remote MCP), then the umbrella (#133–#134).
6. **Out-of-process.** E11 (out-of-process docking), with hpc (#70–#72) as its first user.
7. **Acceptance on DEV.** An external agent completes the research lifecycle over `/api/v1/mcp`
   with a scoped token, recorded with screenshots and logs (paper-scitex-clew QA).
