# API contract v1 — 6. Decisions taken here, 7. How legacy endpoints move

Part of [api-contract-v1.md](../api-contract-v1.md).

## 6. Decisions taken in this document (not escalated)

Each was decided against what is already shipped, to minimise churn. Real before → after examples
come from the 2026-11-27 inventory.

| Topic | Decision | Rationale | Before → after |
|---|---|---|---|
| Base path, versioning | `/api/v1`, with the contract major in the path. Additive-only within v1 (API-C001). | Already shipped in the SDK. Visible in logs and docs. | `/api/project/list/` → `/api/v1/hub/projects` |
| Casing | Paths are kebab-case. JSON, query parameters and enum values are snake_case. | `_NAME_RE` already enforces kebab paths. Snake JSON equals Python handler and MCP argument names. | `api/compile/status` → `writer/jobs/{job_id}`; dataset `min_size_bytes` |
| Trailing slash | None. A slashed path gets a 404 problem with the canonical path as a hint. | One URL per operation. `APPEND_SLASH` redirects break POST. | `/api/v1/scholar/search/` → `/api/v1/scholar/papers` |
| Project scoping | The `project` parameter, as shipped. A package's per-project view is `<pkg>/projects/{project_id}`. | One shape for every leaf. Project-restricted tokens are checked in one place (`api_exec`). | `/<owner>/<slug>/api/file-tree/` → `GET /api/v1/hub/files?project=owner/slug` |
| Search | `list` with `q`. There is no `search` action. | One verb per meaning, as dataset already does. | `/api/v1/scholar/search/?q=` → `/api/v1/scholar/papers?q=` |
| Hierarchical ids | `/` is written as `~` within one segment. | Shipped in dataset. Proxies and Django decode `%2F`. | `huggingface/org/name` → `huggingface:org~name`; `data/raw.csv` → `data~raw.csv` |
| Files | Metadata goes through `hub/files`. Bytes go through signed URLs: `hub/uploads` create returns a PUT URL, and `files` get returns `download_url`. | Every operation stays JSON (MCP-compatible), and large bytes bypass the worker. Three file APIs become one. | `…/files/upload-url/`, `/apps/files/api/upload/`, `/api/workspace/save-file/` → `POST /api/v1/hub/uploads`, `PATCH /api/v1/hub/files/{file_id}` |
| Filters, sorting | Declared named parameters and a `sort` enum. No `filter[]`, no sparse fields. | The shipped validation already refuses unknown parameters. Simple MCP schemas. | dataset `?q=&repository=&modality=` |
| Page size | Declared per operation, with `max_limit ≤ 200`. | Leaves differ in what is cheap. | dataset 20/100 (search), 50/200 (project lists) |
| Jobs | Per-package `jobs` resource with one fixed Job schema. No central job store in v1. | The leaf that runs the job owns its state (Rule L). The Hub sees job ids through the meter. | `/apps/console/api/jobs/<int>/status/` → `GET /api/v1/hpc/jobs/{job_id}` |
| Job webhooks | Post-beta, as an additive optional `callback_url` parameter. | Polling `<pkg>_jobs_get` works for agents now. | — |
| Rate classes | A closed set: `anonymous`, `standard`, `search`, `bulk`, `interactive`, times compute `light`, `standard`, `heavy`. Default numbers from audit §c.7. | Numbers are host configuration, not contract, so they can change without a break. | dataset `rate_class="search"` |
| Request id | Server-generated `X-Request-Id`. A client-sent id is echoed as `X-Client-Request-Id`. | One id per hop that we control. | shipped |
| Metering | No per-call billing and no metering response headers in v1. Meter events only. | Operator: API calls are not billed. | — |
| OAuth, JWT | OAuth 2.1 (PKCE required, device grant) is the agent login, and its access token is a bearer under API-A001. The password JWT is deprecated. | Agents must not store passwords. | `POST /api/token/` → `scitex login` (device flow) |
| `verify` vs `validate` | Clew keeps the action verb `verify` through a justified `cli-audit-dict.yaml` entry. | Provenance verification is not schema validation. It is the paper's and the CLI's term (`clew verify --strict`). | `clew_verify_claim` → `clew_claims_verify` |
| Reserved v1 paths | `operations`, `openapi.json`, `mcp`, `health` (API-R006). | Discovery points that sit outside the package grammar. | `/mcp` → `/api/v1/mcp`; (new) `GET /api/v1/operations` |
| Standards-defined paths | `/.well-known/*`, `/oauth/*`, Git HTTP/SSH and inbound webhooks stay where their standards put them. | Clients find them by standard. | `/.well-known/agent.json` → `/.well-known/agent-card.json` |
| Hub-native endpoints | Declared through the SDK as the `hub` dock, with the same grammar (operator 2026-11-28). | One grammar, with no platform exception. | `/api/me/tokens/` → `GET /api/v1/hub/tokens` |

## 7. How existing non-conforming endpoints move behind the SDK

Every row of the [migration table](04-migration.md) uses exactly one mechanism:

- **Rewrite.** The owning package declares the v1 operation, and the handler moves into that package
  or is written there. Used for lifecycle operations and for every Rule-L violation where the logic
  sits in the Hub.
- **Facade.** The old route stays with its exact response, frozen on the allowlist and sending
  `Deprecation`, `Sunset` and `Link` to the v1 operation. Where cheap, it calls the same handler.
  Used where external users exist (scholar public search), or where UI code depends on the route
  until the UI is ported.
- **Remove.** Deleted with no v1 twin: generic RPC, duplicates, unauthenticated compute. Where
  security is at stake, removal comes first and the v1 twin follows.

**Int (internal-only)** routes are UI JSON, webhooks and status probes. They are not part of the
public contract. They stay on the allowlist under an `internal` category, are never documented, and
are never called by SDK clients. API-E003 still applies when they live under `/api/`.

**Std (standards-defined)** routes keep their standard location and are outside the grammar.
