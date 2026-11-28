# SciTeX public API contract v1

**Status: ACCEPTED (2026-11-28).** Operator decisions 1–11 are all (a). Implementation is tracked as workstreams W1–W5 (§10).

**Audience:** leaf authors, Hub maintainers, the inventory and contract-test owners, and the operator.

| Part | Contents |
|---|---|
| this file | the spine, what already exists, the decision summary, order of work |
| [01-rules.md](api-contract-v1/01-rules.md) | §1 rule registry with stable ids (`API-D/R/V/F/E/A/G/J/I/H/C/T/O`); §2 how a leaf adds an endpoint and what a violation looks like |
| [02-docking.md](api-contract-v1/02-docking.md) | §3 docking (in-process and out-of-process, identity, data, jobs, health, contract versions, one plugin model); §4 `api list` and `GET /api/v1/operations`; §5 three-layer enforcement |
| [03-decisions-taken.md](api-contract-v1/03-decisions-taken.md) | §6 decisions taken without escalation, with rationale and real before → after; §6b the operator's decisions 1–11 (all (a)); §7 rewrite / facade / remove |
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

## 9. Decisions

**Status: DECIDED.** The operator answered "all (a)" for decisions 1–11 on 2026-11-28. The decided text and the alternatives considered are in [03-decisions-taken.md §6b](api-contract-v1/03-decisions-taken.md). In short: (1) MCP names `<package>_<resource>_<verb>`; (2) project id `owner/slug` plus immutable `uid`; (3) v1 frozen at beta, legacy Sunset = beta + 6 months, scholar alias ≥ 12 months; (4) third-party APIs out-of-process only; (5) Hub resources under `/api/v1/hub/`; (6) hosted MCP at `/api/v1/mcp`; (7) every derived operation, scope- and tier-filtered, listed on registries after DEV acceptance; (8) OAuth DCR for public clients with PKCE; (9) USD 40/month promotion budget; (10) the recommended light and public limits profiles; (11) the broad first-phase public list, with PDF compile requiring a key.

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
