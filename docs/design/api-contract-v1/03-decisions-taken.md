# API contract v1 — 6. Decisions taken, 6b. Operator decisions, 7. How legacy endpoints move

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

## 6b. Operator decisions — all DECIDED (a) (operator, 2026-11-28: "all (a)")

These were §9 of the draft. The alternatives are kept as the record of what was considered.



1. **MCP tool name order.** — **DECIDED (a)** (operator, 2026-11-28)
   - Current state: the SDK derives `<package>_<resource>_<verb>` (`dataset_datasets_list`,
     `clew_claims_verify`), and the dataset pilot ships it. scitex-dev §2, which you confirmed, says
     `<pkg>_<verb>_<noun>` (`clew_verify_claim`).
   - **(a) DECIDED:** keep the SDK order for every SDK-derived (public) tool, and amend §2 so the
     auditor checks derived tools by their operation metadata (API-T001). §2 already accepts the
     noun-group form (`dev_ecosystem_list`). This order groups tools by resource and mirrors CLI
     `<noun> <verb>` groups.
   - (b) Change the SDK to `<package>_<verb>_<resource>` (`dataset_list_datasets`). This renames
     the 9 dataset tools now (S), before anything depends on them.
2. **Canonical project id.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** the public id is the handle `owner/slug`.
     - It is already the SDK's `project` parameter, written `owner~slug` inside a path segment.
     - Responses also carry an immutable `uid` (`prj_…`).
     - After a rename, an alias table keeps old handles resolving for the deprecation window.
   - (b) An opaque `prj_…` id is canonical everywhere, and the handle is accepted as an alias. This
     is more stable, but humans and agents must look ids up first, and the shipped dataset contract
     changes.
3. **Deprecation window and v1 freeze.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:**
     - v1 is frozen (additive-only) from beta launch.
     - Legacy routes get `Deprecation` now and `Sunset` = beta + 6 months.
     - `/api/v1/scholar/search/`, which has live users, stays as a frozen alias for at least 12 months.
   - (b) A "v1-beta" period until GA, with breaking changes allowed on 30 days' notice.
   - (c) A 3-month legacy sunset.
4. **Third-party (user-published) apps that expose APIs.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** out-of-process only (API-D009), admitted by the existing AppsModule
     approval with a pinned commit. They follow the same grammar, scopes and metering as
     first-party apps.
   - (b) No third-party APIs at beta; UI facet only.
   - (c) In-process after review.
5. **Path prefix for Hub platform resources.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** `/api/v1/hub/<resource>`. The Hub is a package like any other, so there is
     no grammar exception.
   - (b) Top-level `/api/v1/projects`, `/api/v1/tokens`. URLs are shorter, but this adds special
     cases in the SDK, in scopes and in MCP names.
6. **Hosted MCP endpoint path.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** `https://scitex.ai/api/v1/mcp`. It sits behind the same gateway, rate
     limits and nginx rules as REST, and is versioned with the contract that its tools derive from.
     The OAuth protected-resource URL is unambiguous. Today's `/mcp` stays operator-only until it
     is retired.
   - (b) `https://scitex.ai/mcp`. Shorter, and the current location, but unversioned, outside the
     `/api/v1` gateway, and it collides with the operator umbrella during migration.
   - (c) A separate host, `https://mcp.scitex.ai/`.
7. **Hosted MCP tool set and public listing at beta.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** serve every SDK-derived operation of admitted docks, filtered by token
     scope and tier (public / member / privileged; shell, exec and RPC are never served). List the
     server on the official MCP registry and lobehub **after** the DEV acceptance run, together
     with the product A2A card.
   - (b) A lifecycle-only subset (about 25 operations), widened one at a time.
   - (c) List on registries at beta launch, before the acceptance run.
8. **OAuth client registration for agents and MCP clients.** — **DECIDED (a)** (operator, 2026-11-28)
   - **(a) DECIDED:** Dynamic Client Registration (RFC 7591) for public clients only, with:
     - PKCE required;
     - scopes capped to read plus explicitly consented writes;
     - registration rate-limited;
     - unused clients expired after 90 days.

     Claude and ChatGPT connectors need DCR.
   - (b) Pre-registered clients only.
9. **Monthly internal budget for sponsored public compute** — **DECIDED (a)** (operator, 2026-11-28) (`public_compute` kind on the #1256
   promotion account).
   - **(a) DECIDED:** **USD 40/month**, revisited monthly against funnel data.
     - Alerts fire at 50/80/100 %.
     - A global backstop sits at 1.25 × (download sponsorship + compute budgets).
     - The system runs in shadow mode for the first cycle.
   - (b) USD 30/month.
   - (c) USD 50/month.
   - (d) No sponsored compute; discovery and search only.
10. **Limits for the light class and the public profiles** — **DECIDED (a)** (operator, 2026-11-28) ([06 §12.4](06-public-light.md)).
    - **(a) DECIDED:**

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
11. **Initial public (sponsored) operation list for the first phase.** — **DECIDED (a)** (operator, 2026-11-28) This is config, not contract,
    and can be narrowed later.
    - **(a) DECIDED**, broad as you asked:
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
