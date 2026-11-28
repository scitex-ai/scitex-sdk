# API contract v1 — 1. Rule registry and leaf author guide

Part of [api-contract-v1.md](../api-contract-v1.md).

## 1. Rule registry (stable ids)

Every rule has a stable id. The same id appears in:

- the exception raised at declaration time;
- the contract-test failure;
- the `scitex-dev` audit finding;
- the inventory and `api list` violation tags;
- the Hub's refusal log and `GET /api/v1/hub/docks`.

Ids are never reused. A retired rule keeps its id, marked `retired`.

Families defined in other parts:

- `API-M001`–`M006`, hosted MCP: [05-hosted-mcp.md](05-hosted-mcp.md).
- `API-K001`–`K008` (cost class, exposure ceiling, sponsorship) and `API-Q001`–`Q003` (priority
  classes): [06-public-light.md](06-public-light.md).

**Layer** is where the rule is enforced: **D** = declaration time (the SDK constructor raises),
**C** = CI (the contract test and the `scitex-dev` audit), **R** = runtime (the host refuses or
answers with a problem). **State** is the state on `develop` on 2026-11-28.

### 1.1 Docking and declaration — `API-D`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-D001 | Every public HTTP route under `/api/` and every remote MCP tool is generated from an `ApiOperation` of an admitted plugin. Nothing else is public. | C, R | partial: legacy routes exist |
| API-D002 | A plugin is advertised by entry point `scitex.apis`. Entry-point name = plugin id = package slug. One plugin per distribution. | D, C | shipped |
| API-D003 | A plugin declares `contract="1"` (major). A host refuses to dock an unsupported major, loudly ([02-docking §3.6](02-docking.md)). | D, R | shipped (0.5.0: stored in the descriptor, re-checked at admission) |
| API-D004 | No hand-written JSON route under `/api/` outside the frozen legacy allowlist. The allowlist only shrinks. | C | **new** (Hub test) |
| API-D005 | No catch-all or dynamic dispatcher in a declaration (`<path:endpoint>`, generic `module/function` RPC). | D, C | shipped for `scitex.apis`; legacy dispatchers remain |
| API-D006 | Handlers are `module:function` strings owned by the declaring distribution. They are resolved only after admission. | D, R | shipped |
| API-D007 | The wheel ships the inert descriptor `scitex_api.json`. Out-of-process docking and the catalogue read it without importing the leaf. | C | shipped (hatch hook); not yet adopted by every leaf |
| API-D008 | The package exposes the SDK-provided `scitex-<pkg> api list`, generated from the same declaration ([02-docking §4](02-docking.md)). | C | **new** (inventory owner) |
| API-D009 | Out-of-process docks accept only a host-signed internal identity token, never a raw user credential. | R | **new** |

### 1.2 Resource grammar — `API-R`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-R001 | URL = `/api/v1/<package>/<resource>[/{<resource_singular>_id}][/<action>]`. Nothing deeper. | D | shipped |
| API-R002 | `<package>`, `<resource>` and `<action>` are lowercase kebab-case, `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`. | D | shipped |
| API-R003 | `<resource>` is a plural noun (lexical check: ends in `s`). | D | shipped |
| API-R004 | No trailing slash. `/api/v1/dataset/datasets/` is a 404 problem whose `detail` names the canonical path. | R | partial (404 problem, no hint yet) |
| API-R005 | Project scoping uses the `project` parameter, never path nesting. A package's per-project singleton is the item `<package>/projects/{project_id}`. | D | shipped (`project_scoped=True`) |
| API-R006 | Reserved top-level paths outside the package grammar: `GET /api/v1/operations` (the live operation list), `GET /api/v1/openapi.json`, `/api/v1/mcp` and `GET /api/v1/health`. No package may be named `operations`, `openapi.json`, `mcp` or `health`. | D, R | **new** |
| API-R007 | `<package>` is the distribution name without the `scitex-` prefix (`scitex-live-paper` → `live-paper`, `figrecipe` → `figrecipe`). The Hub is `hub`. | D, C | **new** check |

### 1.3 Verbs, methods and status codes — `API-V`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-V001 | CRUD verbs fix the method, the item-ness and the success status: `list` GET 200 · `get` GET 200 · `create` POST 201 + `Location` · `update` PATCH 200 · `delete` DELETE 204. | D, R | shipped (`Location` since 0.5.0) |
| API-V002 | Every other verb is an action: POST, declared `item=True` (`…/{id}/<verb>`) or `item=False` (`…/<verb>`). The response is 200, or 202 + Job (API-J001). | D | shipped |
| API-V003 | Action verbs come from the canonical verb catalogue (scitex-dev §1d). Anything else needs a justified entry in the package's `.scitex/dev/cli-audit-dict.yaml`. Search is `list` with `q`, never a `search` action. | C | shipped (0.5.0: `api_verbs`, `verb_exceptions:` with `# why`) |
| API-V004 | An action without side effects declares `read_only=True`. It then needs the `read` scope and no idempotency key. | D | shipped |
| API-V005 | Status vocabulary: 400 validation · 401 no or invalid credential · 402 spend cap · 403 scope or CSRF · 404 absent or not yours · 405 method · 409 conflict or idempotency mismatch · 422 domain refusal · 429 rate · 503 dependency or unconfigured. | R | shipped except 422/429 codes |

### 1.4 Fields, ids, time and units — `API-F`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-F001 | JSON fields and query parameters are `snake_case`. Enum values are lowercase `snake_case`. | D | **new** check |
| API-F002 | Timestamps are `*_at`, RFC 3339 UTC with `Z` (`2026-11-28T03:04:05Z`). Calendar dates are `*_date` (`YYYY-MM-DD`). | C | **new** |
| API-F003 | Quantities carry their unit: `*_bytes`, `*_seconds`, `*_count`. Money is `{"amount_minor": int, "currency": "USD"}`. | C | **new** (dataset already uses `min_size_bytes`) |
| API-F004 | Ids are strings in one path segment (`[A-Za-z0-9._:~-]+`). A hierarchical natural key writes `/` as `~` (dataset: `huggingface:org~name`). The path parameter is `<resource_singular>_id`. | D | names shipped; charset check **new** |
| API-F005 | Response shapes: item `{"data": {...}}` · list `{"data": [...], "has_more": bool, "next_cursor": str\|null[, "total": int]}` · accepted `{"job": Job}`. Every resource object has `id`, and a created object also has `created_at`. | R | shipped except the `id` check |

### 1.5 Errors — `API-E`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-E001 | Every error is RFC 9457 `application/problem+json`: `type` (`https://scitex.ai/problems/<code>`), `title`, `status`, `detail`, `code`, `request_id`, `retryable`, `errors[{field, code, message}]`. | R | shipped (`api_exec.ApiProblem`) |
| API-E002 | `code` is `<package>.<snake>` for leaf errors, declared as an `ApiError` on the operation. The SDK uses `api.<snake>`, and host capabilities use `host.<snake>`. The registry is the union of declarations, published in OpenAPI `x-scitex-errors` and `api list --errors`. | D, C | declarations shipped; registry page **new** |
| API-E003 | An API path never answers HTML, never redirects to a login page, and never answers 2xx with an error body. | R, C | shipped under `/api/v1/`; legacy routes violate it |
| API-E004 | "Absent" and "not yours" are the same 404 (`api.not_found`). | R | shipped |

### 1.6 Authentication and scopes — `API-A`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-A001 | A program sends exactly one credential form: `Authorization: Bearer <token>`. The token is a personal access token, a project token or an OAuth access token. A session cookie is accepted only from first-party UI, with CSRF on writes. There is no `X-SCITEX-API-KEY` and no `?api_key=`. | R | shipped in Hub caller; scholar legacy violates it |
| API-A002 | A bearer that is presented but invalid gets 401 with `WWW-Authenticate: Bearer`. It never falls back to anonymous or to the session. | R | shipped |
| API-A003 | Scopes are derived: `<package>:<resource>:<read\|write>`. Wildcards are `*`, `*:read`, `*:write`, `<package>:*`, `<package>:*:<access>` and `<package>:<resource>:*`, and `write` implies `read`. A leaf cannot declare its own scope string. | D, R | shipped (`scope_granted`) |
| API-A004 | Anonymous calls reach only operations that the host's public-tier configuration enables and whose declared `exposure` ceiling is `public_eligible` (API-K001, K008). These calls use the `anonymous` rate class and the `public` priority class. | D, R | **new** |
| API-A005 | Legacy key scopes map as follows: `*` stays `*`; `api` and `mcp` become `*` for operators only; `publish` becomes `live-paper:papers:write`. New UI keys default to `*:read`. | R | **new** |

### 1.7 Lists, filters, sorting — `API-G`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-G001 | Every `list` is cursor-paginated with `?limit=&cursor=`. The default and maximum are declared per operation, with `max_limit ≤ 200`. The cursor is opaque. | D | shipped (no 200 cap yet) |
| API-G002 | Filters are named, declared parameters (`?q=&repository=`), and unknown parameters get 400 `api.unknown_parameter`. Sorting is a declared `sort` enum of `field` / `-field`. There is no `filter[x]` syntax and no sparse fieldsets in v1. | D, R | shipped (unknown → 400) |

### 1.8 Jobs and idempotency — `API-J`, `API-I`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-J001 | A long operation returns 202 `{"job": Job}`. Job = `{id, state ∈ queued\|running\|succeeded\|failed\|canceled, percent, message, result, error (a problem), created_at, updated_at, links: {self}}`. The package exposes `<package>/jobs/{job_id}` `get`, plus a `cancel` action if the job is cancellable. MCP returns the same Job, and agents poll `<package>_jobs_get`. | D, C | partial (dataset Job has 4 fields) |
| API-I001 | Every write requires `Idempotency-Key`. A replay within 24 h returns the stored answer with `Idempotent-Replayed: true`. The same key with different parameters gets 409 `api.idempotency_mismatch`. | R | shipped |

### 1.9 Headers, rate limits, metering — `API-H`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-H001 | Every response carries `X-Request-Id`, equal to `request_id` in a problem body. | R | shipped |
| API-H002 | Rate-limited responses carry `RateLimit-Policy` and `RateLimit` (IETF httpapi draft). A 429 carries `Retry-After` and code `api.rate_limited`. | R | hook exists; headers **new** |
| API-H003 | A deprecated operation or legacy route carries `Deprecation` (RFC 9745), `Sunset` (RFC 8594) and `Link: <…>; rel="deprecation"`. | R | **new** |
| API-H004 | API calls are not billed. The meter hook records one usage event per call: operation, caller, token, project, status, duration and bytes, never bodies. Billable resources (compute, storage, transfer, external services) are metered by their collectors with the same `request_id` / `job_id`. A spend-cap refusal is 402 `host.spend_cap_reached` with `link`. | R | hook shipped; 402 via `StorageRefused` shipped |

### 1.10 Compatibility — `API-C`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-C001 | Within v1, changes are additive only: new operations, new optional parameters, new response fields, new error codes, new response enum values. Anything else is v2. | C | **new** (the contract test diffs against the last released descriptor) |
| API-C002 | Renames and removals go through a deprecation window (API-H003), with the date in `Sunset`, and are listed in `GET /api/v1/hub/changes`. | C | **new** |

### 1.11 MCP — `API-T`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-T001 | A public tool's name is derived: `<package>_<resource>_<verb>`, with `-` → `_` (`dataset_project_datasets_fetch`, `live_paper_papers_create`). | D | shipped |
| API-T002 | Tools and operations map 1:1. The input schema is the request schema plus the item id, and the description names the REST twin and the scope. | D | shipped |
| API-T003 | An umbrella or host mounts derived tools under their own names. It never re-namespaces them, which fixes the ≈238 `clew_clew_*` / `writer_writer_*` names. | C | **new** (scitex-python umbrella) |
| API-T004 | Remote MCP (`/api/v1/mcp`) serves only derived tools of admitted docks, filtered by the token's scopes. Hand-written tools stay local stdio tools. | R | **new** |

### 1.12 OpenAPI — `API-O`

| Id | Rule | Layer | State |
|---|---|---|---|
| API-O001 | OpenAPI 3.1 is generated from the declarations (`ApiPlugin.openapi_fragment()`) and merged at `/api/v1/openapi.json`. `operationId` = `<package>.<resource>.<verb>`. | R | fragment and operationId shipped (0.5.0); merged document **new** |
| API-O002 | The merged document validates (openapi-spec-validator) in the Hub's CI and in each leaf's CI. | C | **new** |

---

## 2. How a leaf author adds an endpoint

This is the whole of the leaf's work. The pattern is the scitex-dataset pilot, applied to clew.

```python
# src/scitex_clew/_rest/__init__.py
from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiError, ApiField, ApiSchema

JOB = ApiSchema("Job", (ApiField("id"), ApiField("state")))   # API-J001 helper fills the rest

OPERATIONS = (
    ApiOperation(
        "clew", "claims", "list", "scitex_clew._rest._handlers:list_claims",
        summary="Claims registered in a project",
        project_scoped=True, paginated=True, default_limit=50, max_limit=200,
    ),
    ApiOperation(
        "clew", "claims", "verify", "scitex_clew._rest._handlers:verify_claim",
        summary="Re-check a claim's minimal DAG against its recorded hashes",
        item=True, response=JOB, project_scoped=True,
        errors=(ApiError("clew.claim_not_found", 404, "No such claim"),),
        compute_cost="heavy",
    ),
)
PLUGIN = build_plugin("clew", "SciTeX Clew API", "1", OPERATIONS)
```

```toml
# pyproject.toml
[project.entry-points."scitex.apis"]
clew = "scitex_clew._rest:PLUGIN"
```

```python
# src/scitex_clew/_rest/_handlers.py
from scitex_sdk.app.api_exec import ApiCall, ApiJob, ApiPage

def list_claims(call: ApiCall) -> ApiPage:      # call.project is the host's ProjectAccess
    rows = _store(call.project).claims(offset=call.offset, limit=call.limit + 1)
    return ApiPage(rows[: call.limit], has_more=len(rows) > call.limit)

def verify_claim(call: ApiCall) -> ApiJob:
    return ApiJob(_jobs.submit("verify", claim_id=call.id, project=call.project))
```

From those lines alone, every host derives:

| Derived | `clew.claims.list` | `clew.claims.verify` |
|---|---|---|
| REST | `GET /api/v1/clew/claims?project=owner/slug&limit=&cursor=` → 200 | `POST /api/v1/clew/claims/{claim_id}/verify` → 202 |
| Scope | `clew:claims:read` | `clew:claims:write` |
| MCP | `clew_claims_list(project, limit?, cursor?)` | `clew_claims_verify(claim_id, project)` |
| Idempotency | – | `Idempotency-Key` required |
| OpenAPI `operationId` | `clew.claims.list` | `clew.claims.verify` |
| `scitex-clew api list`, `scitex api list`, `GET /api/v1/operations` | one row | one row |

**What a violation looks like today.** These messages came from running the code on `develop` on 2026-11-28:

```text
ApiOperation("clew", "data", "list", ...)
  ApiPluginContractError: resource 'data' must be a plural noun
ApiOperation("clew", "Claims", "list", ...)
  ApiPluginContractError: resource 'Claims' must be lowercase kebab-case ([a-z][a-z0-9-]*)
ApiOperation("clew", "claims", "verify", ...)             # item= not stated
  ApiPluginContractError: action 'verify' must state item=True or item=False
ApiOperation("clew", "claims", "get", ..., paginated=True)
  ApiPluginContractError: only a list operation is paginated
```

**v1 change (sdk, S):** the same exception carries the rule id, the operation id and the rule's anchor.
`ApiPluginContractError` gains a `rule` attribute, and existing `except` clauses keep working:

```text
ApiPluginContractError: [API-R003] clew.data.list: resource 'data' must be a plural noun
  (docs/design/api-contract-v1/01-rules.md#12-resource-grammar--api-r)
```

The contract test, the `scitex-dev` audit, `api list --check` and the Hub refusal log print the same
line.
