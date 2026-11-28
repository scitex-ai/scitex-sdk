# API contract v1: 11. Hosted MCP

Part of [api-contract-v1.md](../api-contract-v1.md).

> Operator, 2026-11-28: "consider to provide mcp tools over the internet; this way, for example,
> external agents who know the url" (and a key) can use SciTeX.

**Hosted MCP is the REST contract served over the MCP transport.** It is not a second API:

- Every tool is generated from the same `ApiOperation` declarations as REST (`api_mcp.tool_specs`,
  shipped), so the REST↔MCP 1:1 mapping holds by construction (API-T002).
- Docking a leaf gives it hosted MCP tools with no further work. Undocking removes them.
- Every tool call runs `api_exec.execute`, the same function REST runs. Scope checks, parameter
  validation, project authorization, handlers and result shapes are therefore identical.

## 11.1 Endpoint

| Item | v1 |
|---|---|
| URL | **`https://scitex.ai/api/v1/mcp`** (recommended; decision 6), one endpoint on the Hub origin |
| Transport | MCP streamable HTTP, current specification revision (2025-06-18 or later, negotiated in `initialize`). The deprecated HTTP+SSE transport is not offered. |
| Sessions | Stateless: no server-held session is required, so any worker can answer. `Mcp-Session-Id` is accepted and echoed but carries no state. Jobs (API-J001) carry long work instead of streams. |
| Protocol surface | `initialize`, `tools/list`, `tools/call`, `ping`. No resources, prompts or sampling in v1 (additive later). |
| Rule ids | API-T001–T004, plus API-M001–M006 below |

| Id | Rule | Layer | State |
|---|---|---|---|
| API-M001 | Hosted tools are exactly `tool_specs(plugin)` of admitted docks. There is no hand-written hosted tool and no umbrella re-export. | R, C | **new** (today `/mcp` serves the 617-tool umbrella) |
| API-M002 | `tools/list` returns only the tools the caller's scopes grant (`scope_granted`), and only tools whose tier the caller's account has reached (§11.4). | R | **new** |
| API-M003 | Authentication failures are transport-level HTTP 401/403 with `WWW-Authenticate` (MCP authorization spec). Tool failures are tool results with `isError: true` whose `structuredContent` is the full problem object (API-E001, including `request_id`). Unknown tool or malformed arguments: JSON-RPC `-32602`. | R | partial: `api_mcp` raises `ToolError` with `{status, code, detail}` only |
| API-M004 | A successful tool result carries the REST body as `structuredContent` (`{data…}` / `{data, has_more, next_cursor}` / `{job}`) and the same JSON as text content. `_meta` carries `request_id` and `operation_id`. | R | **new** |
| API-M005 | Every `tools/call` passes through the same rate limiter, meter (`transport: "mcp"`), idempotency and spend hooks as REST. For a write tool, `Idempotency-Key` = the JSON-RPC request id scoped to the token, unless the client sends `_meta.idempotency_key`. | R | **new** |
| API-M006 | A synchronous tool call has a 30 s budget. Anything longer must be declared async and returns a Job. | D, R | **new** |

## 11.2 Authentication

- **Agents and programs:** `Authorization: Bearer <token>` on every HTTP request (API-A001). A
  personal access token works, and a project token (`scitex_prj_…`) restricts the session to one
  project. "Know the URL plus a key" is enough:

  ```bash
  claude mcp add --transport http scitex https://scitex.ai/api/v1/mcp \
    --header "Authorization: Bearer $SCITEX_TOKEN"
  ```

- **Interactive clients** (Claude, ChatGPT and IDE connectors) use OAuth 2.1 per the MCP
  authorization specification:
  - **Discovery.** An unauthenticated request gets 401 with
    `WWW-Authenticate: Bearer resource_metadata="https://scitex.ai/.well-known/oauth-protected-resource/api/v1/mcp"`.
    That document follows RFC 9728 and names the authorization server, whose metadata follows
    RFC 8414 at `/.well-known/oauth-authorization-server`.
  - **Authorization.** Authorization code with **PKCE S256 required**. Resource indicators
    (RFC 8707) bind each token to `https://scitex.ai/api/v1/mcp`, so a token minted for MCP is not
    a general REST token unless its audience says so.
  - **Scopes** are the derived API-A003 scopes, and consent screens list them. Step-up uses 403
    `insufficient_scope` with the required scope.
  - **Client registration:** decision 8.
- **Gaps against the Hub today** (audit 2026-11-27), all fixed in E10/E16:
  - django-oauth-toolkit offers only the scopes `openid profile email`;
  - PKCE is not enforced;
  - there is no device grant;
  - there is no protected-resource metadata;
  - the DRF and SDK caller do not accept OAuth bearers;
  - `/mcp` requires a superuser key with scope `mcp` or `*`.
- **Per-project scoping.**
  - Project-scoped tools take `project` (`owner/slug`) like REST.
  - With a project token, `tools/list` presents `project` as optional and defaulted to the
    token's project. Any other value gets 403 (`api_exec` already enforces the restriction).
  - With a personal token, `project` is required and authorized by the Hub's `project_access`.

## 11.3 Same generic layer as REST

| Concern | REST | Hosted MCP |
|---|---|---|
| Identity | `SCITEX_API_CALLER` | the same hook, on the MCP HTTP request |
| Scope | `scope_granted` in `execute` | the same check, plus `tools/list` filtering (API-M002) |
| Rate limit | `SCITEX_API_RATE_LIMITER`, per token (or per IP when anonymous) | the same buckets: one `tools/call` = one operation call; `tools/list` and `initialize` are `standard` class |
| Metering | `SCITEX_API_METER`, one event per call, never bodies | the same, with `transport: "mcp"` and the JSON-RPC id; not billed (API-H004) |
| Request id | `X-Request-Id` | `X-Request-Id` header on the HTTP response, plus `_meta.request_id` per tool result |
| Errors | problem+json | problem object in the `isError` result (API-M003) |
| Spend cap | 402 `host.spend_cap_reached` | the same problem in the `isError` result, with `link` |

## 11.4 Exposure tiers and abuse controls

| Tier | Who | Tools | Controls |
|---|---|---|---|
| **public** | no credential (or a low-trust key) | operations enabled in the public-tier **configuration** ([06 §12.4](06-public-light.md); first phase: search and describe, stats tests, figure plotting, and PDF compile with a key) | sponsored (promotion account); `public` priority class; per-IP and per-key buckets; public limits profiles; no storage writes |
| **member** | any valid token | every derived operation with `exposure` of `member` or `public_eligible` that the scopes grant | per-token buckets (audit §c.7 defaults); concurrent jobs ≤ 10; spend caps (#1242); `member` or `paid` priority class |
| **privileged** | token with an explicit privileged scope **and** an account flag (verified email, payment method on file, not in trial) | operations declared `exposure="privileged"` that run user-supplied code or reach external compute: `hpc_jobs_create`, future container exec | not covered by `*`, `*:write` or `<pkg>:*` wildcards (the scope must be named); concurrency 1–2; spend cap required; audit log |
| **never** | nobody, over any transport | shell, `execute`, `command`, notebook kernels, console services, the generic `scitex/<module>/<function>` RPC, agent-container operations, umbrella hand-written tools | never declared as operations (API-D001/D005); refused by the Hub allowlist test |

**Low-trust keys** are keys from accounts younger than 7 days or with an unverified email. They get
half the member buckets, no privileged tier, and 1 concurrent job. The thresholds are host
configuration, not contract.

**SDK addition (E16):** `ApiOperation(exposure="privileged")` (API-K001). It derives a scope with a
`:privileged` suffix that wildcards do not match, and `tools/list` hides the tool unless the account
flag holds.

## 11.5 Discovery

- **Live listing.** `GET /api/v1/operations` (API-R006) rows include `mcp_tool`, `tier` and
  `transport: ["rest","mcp"]`. `scitex api list` prints the same rows locally.
- **OAuth metadata** (standard, required): `/.well-known/oauth-protected-resource/api/v1/mcp` and
  `/.well-known/oauth-authorization-server`.
- **Server card:** `/.well-known/mcp.json` gives the endpoint URL, transport, protocol versions,
  auth metadata URL, docs URL and tool count. It follows the MCP server-card proposal's shape and
  is updated additively when that standard settles.
- **A2A.** The fleet-facing card at `/.well-known/agent.json` (it advertises the orochi fleet and has
  registry `not_configured`) conflicts with the product. It is replaced on the product origin by a
  product card at `/.well-known/agent-card.json` that points at `/api/v1/mcp`, and the fleet A2A
  surface moves to `a2a.scitex.ai` (migration #51, #52). The 1.4 k requests already hitting
  `agent-card.json` with a 404 then succeed.
- **Registry listing** (official MCP registry, lobehub): decision 7.

## 11.6 Migration of today's hosted MCP

| Step | Change | Rows |
|---|---|---|
| 1 | Freeze `/mcp`: operators only, unchanged, with `Deprecation`. No new customers. | #50 |
| 2 | Launch `/api/v1/mcp` serving derived tools of admitted docks only. Day one has the 9 `dataset_*` tools, and each leaf adds tools as it docks (#78–#122). | E10, E16 |
| 3 | The umbrella mounts derived tools without re-namespacing (API-T003). The ≈238 double-prefixed names and the `cloud_*`/`hub_*` duplicates disappear from every surface. | #133–#135 |
| 4 | Remove the MCP-as-REST bridge `/api/v1/tools/…` and `/api/mcp/tools/`. | #47–#49 |
| 5 | Retire `/mcp`. Local stdio `scitex mcp start` keeps the full local tool set for the user's own machine. | #50 |

The 617 umbrella tools are not migrated one by one. A hosted tool exists exactly when its operation
is declared, so the hosted set grows with docking. Tools with no operation stay local stdio tools.

## 11.7 End-to-end example: URL + key, list tools, search datasets

```bash
MCP=https://scitex.ai/api/v1/mcp
AUTH="Authorization: Bearer $SCITEX_TOKEN"     # a member token with dataset:datasets:read
H='-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream"'

# 1. initialize
curl -s $MCP -H "$AUTH" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{
  "jsonrpc":"2.0","id":1,"method":"initialize",
  "params":{"protocolVersion":"2025-06-18","capabilities":{},
            "clientInfo":{"name":"example-agent","version":"0.1"}}}'

# 2. list the tools this key may use
curl -s $MCP -H "$AUTH" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
#  -> {"result":{"tools":[{"name":"dataset_datasets_list",
#        "description":"Search openly available datasets ... (REST GET /api/v1/dataset/datasets; scope dataset:datasets:read)",
#        "inputSchema":{"type":"object","properties":{"q":{"type":"string"}, "...":{}, "limit":{"type":"integer"},"cursor":{"type":"string"}},
#                       "required":[],"additionalProperties":false}}, ...]}}

# 3. one dataset search
curl -s $MCP -H "$AUTH" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{
  "jsonrpc":"2.0","id":3,"method":"tools/call",
  "params":{"name":"dataset_datasets_list","arguments":{"q":"eeg motor imagery","limit":3}}}'
#  -> {"result":{"isError":false,
#        "structuredContent":{"data":[{"id":"openneuro:ds...","title":"...", "...":"..."}],
#                             "has_more":true,"next_cursor":"eyJvIjozfQ"},
#        "content":[{"type":"text","text":"{...same JSON...}"}],
#        "_meta":{"request_id":"9f…","operation_id":"dataset.datasets.list"}}}
```

The REST twin of step 3 returns the same body:
`GET /api/v1/dataset/datasets?q=eeg%20motor%20imagery&limit=3`.

This example becomes the hosted-MCP acceptance test. It runs in CI against the SDK standalone host
and on DEV against the Hub (order of work, step 7).
