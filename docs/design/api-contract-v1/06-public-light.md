# API contract v1 — 12. Cost class, priority, and the sponsored public tier

Part of [api-contract-v1.md](../api-contract-v1.md).

> Operator, 2026-11-28: "light computation can be publicly available; we can think of this as a
> commercial [promotion] fee; set an internal budget and handle this public fee internally."
> And: "paid users can use resources with priority; but we can provide various light computation
> like figure plotting, statistical tests, PDF compilation, ... especially during this first phase."

## Existing pieces this section ties together

This section builds no new billing system. It ties together pieces that already exist:

- **Cost class:** `ApiOperation.compute_cost ∈ {light, standard, heavy}` is already declared on every
  operation (shipped; the default is `light`).
- **Spend controls:** scitex-hub #1242 (merged) provides a monthly cap, 50/80/100 % alerts, a hard
  stop, and shadow mode first.
- **Sponsorship of public downloads:** pricing decision #6 / follow-up (c), scitex-hub #1256.
  - Usage with no authenticated requester is charged to a SciTeX **promotion account**.
  - The cap is 50 GB/month per project plus a global backstop, and usage is rate-limited above it.
- **Credit-based billing:** pricing decision #11. API calls are not billed. The usage they trigger
  draws down a credit balance.

Sponsored public API calls become a second **sponsored usage kind**, `public_compute`, on the #1256
promotion account, next to `public_download_egress`. The kind has its own budget line. The rating
rule, spend-control machinery and alerts are the same ones the downloads use.

## 12.1 Declaration vs configuration

The **declaration** (code, part of the contract) says what an operation *is*. The **public-tier
configuration** (host config, not contract) says who may call it for free today. Because of that
split, the first-phase public set can be narrowed later without changing any path, name, schema or
scope. No path, tool name or scope ever contains "free" or "public".

| Id | Rule | Layer | State |
|---|---|---|---|
| API-K001 | Every operation declares `compute_cost ∈ {light, standard, heavy}` (closed set) and `exposure ∈ {public_eligible, member, privileged}`. `exposure` is a **ceiling**: `privileged` operations can never be made public by configuration, and `member` operations (anything that writes project storage or calls a paid external API with the caller's data) cannot either. | D | `compute_cost` shipped (recommended set only); `exposure` **new** |
| API-K002 | **Light** is concrete and measured per call by the host. Every one of these holds: CPU ≤ 1 CPU-second · peak memory above baseline ≤ 256 MiB · wall ≤ 5 s · response ≤ 1 MiB · no project storage write · no paid external API · synchronous (no Job). `standard` and `heavy` are bounded per call by the operation's limits profile (§12.4). | D, R | **new**; thresholds are decision 10 |
| API-K003 | Measured usage above the declared class or profile is **flagged** in the meter event: `cost_class_exceeded: [cpu\|memory\|wall\|bytes\|storage_write\|external]`. If more than 1 % of a UTC day's calls are flagged, the operation is removed from the public tier automatically (it then needs a member token). This alerts the owning package (card) and shows in `GET /api/v1/operations` as `public: false, reason: cost_class_exceeded`. | R, C | **new** |
| API-K004 | The contract test runs every `public_eligible` operation on its declared example inputs under its class or profile limits, and fails when the operation exceeds them. | C | **new** |
| API-K005 | A sponsored call (an operation enabled in the public-tier config, called anonymously or with a trial key) is rated to the **SciTeX promotion billing account**, usage kind `public_compute`. The caller's credit balance is never drawn. A paying member's call is rated to that member as usual. | R | **new**; reuses #1256 |
| API-K006 | Exhaustion of the budget never fails silently (§12.5). | R | **new** |
| API-K007 | Shadow first. K003 and K005 record and report only. Enforcement starts after one clean production release cycle with no false blocks, the same as #1242. | R | **new** |
| API-K008 | The public-tier configuration (`SCITEX_API_PUBLIC_TIER`, §12.4) is the only switch. Each entry gives an operation id plus `public`, `limits` and `priority`. Changing it is a deploy-config change, logged, and reflected live in `GET /api/v1/operations`. | R | **new** |

### How the SDK measures

- `execute` wraps the handler and records wall time and thread CPU time (`time.thread_time`).
- The storage-write and external-call flags are exact. A handler can do either only through a
  `scitex_sdk.host` capability, and the capability sets the flag.
- Peak memory is reported per call by out-of-process services and job sandboxes (cgroup
  `memory.peak`). In-process it is sampled with `tracemalloc` on 1 % of calls.
- All flags travel in the one meter event (API-H004).

## 12.2 Priority classes

| Class | Caller | Queues and slots | Rate limits | Timeouts |
|---|---|---|---|---|
| `paid` | member with an active paid plan or org billing account | highest scheduler priority; reserved share of every pool (≥ 60 %) | plan buckets | the operation's full limits |
| `member` | trial key, or a key without a paid plan | normal priority; may use idle `paid` capacity, is preempted from the queue head when paid work waits | trial buckets | the operation's limits |
| `public` | anonymous caller, or a low-trust key | lowest priority; capped share of each pool (≤ 20 %); **queued or deferred under load, never starving `paid`** | per-IP / per-key `anonymous` buckets | the public profile limits (§12.4) |

| Id | Rule | Layer | State |
|---|---|---|---|
| API-Q001 | The host assigns the priority class from the caller (never from a request parameter) and applies it to job scheduling, concurrency slots, rate buckets and timeouts. | R | **new** |
| API-Q002 | Every response carries `SciTeX-Priority-Class: paid\|member\|public`. A Job adds `priority_class`, `queued_seconds` and, while waiting, `queue_position`. A deferral (pool full for this class) is a 202 Job in `queued` state with `message` saying why, or a 503 `api.capacity_deferred` with `Retry-After` for synchronous operations. It is never a silent stall. | R | **new** |
| API-Q003 | `paid` work is never queued behind `member` or `public` work. A pool reserves the `paid` share even when it is idle. | R | **new** |

Hosted MCP returns the same fields in the Job and `_meta.priority_class`
([05](05-hosted-mcp.md)).

## 12.3 Who may call

| Caller | Operation enabled in the public tier | Any other operation |
|---|---|---|
| anonymous | yes. Sponsored. `public` class. REST and hosted MCP. | 401 |
| trial key or key without a paid plan | yes. Sponsored. `member` class. | per the trial credit |
| paid member | yes. Rated to the member. `paid` class. | per plan |

Abuse controls on sponsored calls:

- per-IP buckets for anonymous callers (IPv6 aggregated to `/64`) and per-key buckets for keys;
- a per-IP daily ceiling;
- no project storage writes; outputs are ephemeral (signed URL, 24 h), and their egress is rated
  under #1256;
- the nginx IP limit as a backstop on `/api/v1/*`.

Low-trust keys ([05 §11.4](05-hosted-mcp.md)) are treated as anonymous.

## 12.4 First-phase public set: configuration with recommended defaults

The operator asked for a broad first phase: figure plotting, statistical tests, PDF compilation,
and search/describe. All of it is configuration under `SCITEX_API_PUBLIC_TIER`, and each entry must
pass API-K004 before it is enabled. Decision 11 confirms the list; decision 10 confirms the limits.

```python
# Hub settings (deploy config; not contract). Keys are operation ids.
SCITEX_API_PUBLIC_TIER = {
    "dataset.datasets.list":          {"public": True, "limits": "light"},
    "dataset.datasets.get":           {"public": True, "limits": "light"},
    "dataset.curated-datasets.list":  {"public": True, "limits": "light"},
    "dataset.curated-datasets.get":   {"public": True, "limits": "light"},
    "scholar.papers.list":            {"public": True, "limits": "light"},
    "scholar.sources.list":           {"public": True, "limits": "light"},
    "clew.hashes.get":                {"public": True, "limits": "light"},
    "live-paper.papers.get":          {"public": True, "limits": "light"},   # published papers only
    "stats.tests.list":               {"public": True, "limits": "light"},
    "stats.tests.get":                {"public": True, "limits": "light"},
    "stats.tests.recommend":          {"public": True, "limits": "light"},
    "stats.tests.run":                {"public": True, "limits": "stats-inline"},
    "stats.descriptives.run":         {"public": True, "limits": "stats-inline"},
    "stats.effect-sizes.run":         {"public": True, "limits": "stats-inline"},
    "stats.power-analyses.run":       {"public": True, "limits": "stats-inline"},
    "stats.corrections.run":          {"public": True, "limits": "stats-inline"},
    "stats.bootstrap-cis.run":        {"public": True, "limits": "stats-bootstrap"},
    "figrecipe.figures.create":       {"public": True, "limits": "figure-inline"},
    "writer.manuscripts.compile":     {"public": True, "limits": "pdf-compile-public",
                                       "requires": "key"},   # anonymous: no; any key: yes
}
```

Recommended limits profiles (per call or per job, public class only; members and paid get the
operation's normal limits):

| Profile | Input | CPU / memory | Wall | Output | Other |
|---|---|---|---|---|---|
| `light` | request ≤ 256 KiB | ≤ 1 CPU-s / 256 MiB | 5 s | ≤ 1 MiB | API-K002 |
| `stats-inline` | inline data ≤ 100 k values | ≤ 2 CPU-s / 512 MiB | 10 s | ≤ 1 MiB | sync |
| `stats-bootstrap` | ≤ 100 k values, `n_boot` ≤ 10 000 | 1 core / 1 GiB | 30 s | ≤ 1 MiB | Job; public pool |
| `figure-inline` | inline data ≤ 100 k points, ≤ 12 panels | 1 core / 1 GiB | 20 s | PNG/SVG/PDF ≤ 5 MB, ephemeral URL 24 h | Job; no storage write |
| `pdf-compile-public` | source bundle ≤ 20 MB, ≤ 200 files, no shell-escape | 2 cores / 2 GiB | 120 s | PDF ≤ 50 pages, ≤ 20 MB, ephemeral URL 24 h | Job; **out-of-process** sandbox (below); dedicated small pool |

The sandbox for public PDF compilation:

- **Out-of-process.** The writer dock stays in-process for its light operations. Its compile Job
  executes in a **separate sandboxed pool**: a container with a read-only root, a tmpfs workdir,
  `--network none`, no-new-privileges, a seccomp default profile, a non-root uid, and
  `-no-shell-escape`.
- **Pool size.** 2 concurrent slots for the `public` class, separate from the member and paid
  compile pool.
- **Over the limits.** The Job ends `failed` with problem `writer.limits_exceeded`, which names the
  limit (pages, wall, size).

Never public (`exposure` ceiling `member` or `privileged`):

- anything writing project storage;
- LLM or other paid external APIs;
- dataset fetch into a project;
- HPC jobs;
- container exec.

## 12.5 Budget, alerts, backstop, degradation

These reuse the #1242 machinery, with the promotion account as the payer.

- **Monthly internal budget** for `public_compute`. Decision 9 recommends **USD 40/month** to start,
  revisited monthly against funnel data.
- **Alerts** at 50 %, 80 % and 100 % go to dev@ (ops alerts) through #1242's alert path.
- **Global backstop.** A hard ceiling over all sponsored kinds (download egress plus public compute)
  equal to the sum of the kind budgets × 1.25. It guards against mis-accounting in any single kind.
- **Degradation** when the `public_compute` budget is exhausted, for the rest of the UTC month:
  1. Anonymous calls get **401** problem `api.sponsorship_exhausted`. `detail` says a key restores
     access, `link` points to key creation, and the response sends `WWW-Authenticate`.
  2. Trial keys keep access at half rate, in the `public` priority class.
  3. At the global backstop, sponsored calls get **429** `api.sponsorship_exhausted` with
     `Retry-After` set to the 1st of next month 00:00 UTC.
  4. Paying members are unaffected.
  5. The state is visible in `GET /api/v1/health` (`sponsorship: ok|degraded|exhausted`) and on the
     status page.

  Exhaustion is never a 200 with empty data and never an HTML page (API-E003).
- **Shadow first** (API-K007). For one cycle the system records ratings, alerts and would-be
  degradations, and refuses nothing.
