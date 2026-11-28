# API contract v1 — 8. Migration table

Part of [api-contract-v1.md](../api-contract-v1.md).

**Source.** The 2026-11-27 audit inventory (scitex-hub #1245), plus the `origin/develop` URLconfs
read on 2026-11-28 (`config/urls_api.py`, `public_app/urls/api.py`, `platform_app/urls/api.py`,
`workspace_api/urls.py`).

**Regeneration.** When the generated inventory (`scitex-sdk api inventory`,
[02-docking §4](02-docking.md)) lands, this table is regenerated from its JSON. Any row the
inventory finds that is missing here is added with the same columns. Paths in one family that share
a mapping are one row, which states how many members it has.

**Legend.**

| Column | Values |
|---|---|
| Mech | **Rewrite**, **Facade** or **Remove** (see [03 §7](03-decisions-taken.md)); **Int** = internal-only, kept on the allowlist; **Std** = standards-defined, outside the grammar; **Done** = already v1 |
| Brk | breaking for an existing caller: y / n |
| Eff | S ≤ 1 day, M = 2–4 days, L = 1–2 weeks |
| Pre | **P** = must land before beta; **F** = can follow behind a stable v1 facade |

## 8.1 Hub platform (the `hub` dock)

| # | Current | v1 path | MCP | Owner | Mech | Brk | Eff | Pre |
|---|---|---|---|---|---|---|---|---|
| 1 | `POST /api/token/` (password → JWT) | — (OAuth device grant at `/oauth/`) | — | hub | Facade→Remove | y | M | F |
| 2 | `POST /api/token/refresh/` | — (OAuth refresh) | — | hub | Facade→Remove | y | S | F |
| 3 | `GET /api/me/` | `GET /api/v1/hub/users/{user_id}` (`me` alias) | `hub_users_get` | hub | Rewrite+Facade | n | S | P |
| 4 | `POST /api/me/token/` (password mint, scope `publish`) | `POST /api/v1/hub/tokens` (authenticated) | — (no token tools) | hub | Rewrite+Facade | y | M | P |
| 5 | `GET /api/me/tokens/` | `GET /api/v1/hub/tokens` | — | hub | Rewrite+Facade | n | S | P |
| 6 | `DELETE /api/me/token/<int>/` | `DELETE /api/v1/hub/tokens/{token_id}` | — | hub | Rewrite+Facade | n | S | P |
| 7 | (none) rotate | `POST /api/v1/hub/tokens/{token_id}/rotate` | — | hub | Rewrite | n | S | P |
| 8 | `/accounts/settings/api-keys/` (HTML, default scope `*`) | UI; default `*:read` (API-A005) | — | hub | Int | n | S | P |
| 9 | `POST /api/project/create/` | `POST /api/v1/hub/projects` | `hub_projects_create` | hub | Rewrite+Facade | n | S | P |
| 10 | `GET /api/project/list/` (pagination ignored) | `GET /api/v1/hub/projects` | `hub_projects_list` | hub | Rewrite+Facade | n | S | P |
| 11 | (none) get project | `GET /api/v1/hub/projects/{project_id}` | `hub_projects_get` | hub | Rewrite | n | S | P |
| 12 | `/api/project/switch/` | — (UI session state) | — | hub | Int | n | S | F |
| 13 | `/api/project/scope/` | — (UI) | — | hub | Int | n | S | F |
| 14 | `/api/project/check-name/` (+ `/project/api/check-name/` redirect) | `POST /api/v1/hub/projects/validate` (read-only) | `hub_projects_validate` | hub | Rewrite+Facade | n | S | F |
| 15 | `/<o>/<s>/api/file-tree/` | `GET /api/v1/hub/files?project=&prefix=` | `hub_files_list` | hub | Rewrite+Facade | n | M | P |
| 16 | `/<o>/<s>/api/files/{upload,upload-url}/` | `POST /api/v1/hub/uploads` (signed PUT URL) | `hub_uploads_create` | hub | Rewrite+Facade | n | M | P |
| 17 | `/<o>/<s>/api/files/create/` | `POST /api/v1/hub/files` | `hub_files_create` | hub | Rewrite+Facade | n | S | P |
| 18 | `/<o>/<s>/api/files/delete/` | `DELETE /api/v1/hub/files/{file_id}` | `hub_files_delete` | hub | Rewrite+Facade | n | S | P |
| 19 | `/<o>/<s>/api/files/{rename,move}/` | `POST /api/v1/hub/files/{file_id}/move` | `hub_files_move` | hub | Rewrite+Facade | n | S | F |
| 20 | `/<o>/<s>/api/files/copy/` | `POST /api/v1/hub/files/{file_id}/copy` | `hub_files_copy` | hub | Rewrite+Facade | n | S | F |
| 21 | `/<o>/<s>/api/files/extract-bundle/` | `POST /api/v1/hub/files/{file_id}/extract` (202) | `hub_files_extract` | hub | Rewrite+Facade | n | S | F |
| 22 | `/<o>/<s>/api/files/symlink/` | — | — | hub | Int | n | S | F |
| 23 | `/<o>/<s>/api/git/*` | — (Git over HTTP/SSH is the API) | — | hub | Int | n | S | F |
| 24 | `/<o>/<s>/api/concatenate/`, `/<o>/<s>/api/app/*` | — (UI) | — | hub | Int | n | S | F |
| 25 | `GET /api/workspace/file-content/<path>` (≈240 k 404 loop) | `GET /api/v1/hub/files/{file_id}` | `hub_files_get` | hub | Facade→Remove | n | S | P |
| 26 | `POST /api/workspace/save-file/` | `PATCH /api/v1/hub/files/{file_id}` | `hub_files_update` | hub | Facade→Remove | n | S | F |
| 27 | `/apps/files/api/{list,upload,mkdir,rename,move,delete}/`, `download/`, `raw/` (8) | `hub/files` + `hub/uploads` (`mkdir` = `files create kind=directory`) | `hub_files_*` | hub | Facade→Remove | n | M | F |
| 28 | `/platform/api/context/` | `hub/users/me` + `hub/projects/{project_id}` | — | hub | Remove | n | S | F |
| 29 | `/platform/api/data/<app>/<schema>/…` (3) | — (leaf-owned tables, [02 §3.4](02-docking.md)) | — | hub | Remove | n | M | F |
| 30 | `/platform/api/files/<app>/[<path>]` (2) | `hub/files` | — | hub | Remove | n | S | F |
| 31 | `/platform/api/jobs/<app>/{submit,<uuid>,<uuid>/cancel,}` (4) | `<package>/jobs` | — | hub | Remove | n | M | F |
| 32 | `/platform/api/scitex/<module>/<function>/` (generic RPC) | — | — | hub | **Remove** | n | S | P |
| 33 | `/platform/api/external/<api>/` | — (each leaf declares its external-service operation, metered) | — | hub | Remove | n | M | F |
| 34 | `POST /api/events/` | `POST /api/v1/hub/events` | `hub_events_create` | hub | Rewrite+Facade | n | S | F |
| 35 | `GET /api/events/list/` | `GET /api/v1/hub/events` | `hub_events_list` | hub | Rewrite+Facade | n | S | F |
| 36 | `POST /api/apps/submit/` | `POST /api/v1/hub/app-submissions` | `hub_app_submissions_create` | hub | Rewrite+Facade | n | S | F |
| 37 | `/api/apps/webhook/`, `/api/gitea/webhook/sync/` (HMAC, PR #1244) | — (inbound webhook) | — | hub | Std | n | S | F |
| 38 | `/billing/webhook/stripe/` | — (inbound webhook) | — | hub | Std | n | S | F |
| 39 | `/api/users/search/` | `GET /api/v1/hub/users?q=` | `hub_users_list` | hub | Rewrite+Facade | n | S | F |
| 40 | `/api/search/` (header search) | — (UI) | — | hub | Int | n | S | F |
| 41 | `/apps/llm/api/{chat,chat/stream,…}` | — (UI) | — | hub | Int | n | S | F |
| 42 | `/apps/llm/api/{usage,usage/limits}` | `GET /api/v1/hub/usage-summaries` (post-beta) | `hub_usage_summaries_list` | hub | Int→Rewrite | n | M | F |
| 43 | `/apps/comms/api/…`, `/apps/my-projects/api/…`, `/apps/create/<slug>/api/{chat,apply,run}/` | — (UI) | — | hub | Int | n | S | F |
| 44 | `/api/{status,public-status,server-status,server-health,versions}/`, `/api/server-metrics/{history,export,series}/` (8) | `GET /api/v1/health` + `GET /api/v1/hub/docks`; the rest internal (status worker) | `hub_docks_list` | hub | Int+Rewrite | n | S | P |
| 45 | `/api/landing/github-counts/` | — | — | hub | Int | n | S | F |
| 46 | `/healthz/` | stays (infra probe) | — | hub | Std | n | S | F |
| 47 | `/api/mcp/tools/` | — (duplicate of #48) | — | hub | Remove | n | S | P |
| 48 | `GET /api/v1/tools/` (anonymous listing) | — (`/api/v1/mcp` `tools/list`, `/api/v1/operations`) | — | hub | Facade→Remove | n | S | P |
| 49 | `/api/v1/tools/<auto>/` (617 tools, superuser) | — (each tool's REST twin) | — | hub | Remove | n | S | P |
| 50 | `/mcp` (superuser umbrella) | `/api/v1/mcp` (derived tools, scoped, OAuth) | all derived | hub + sdk | Rewrite | y | M | P |
| 51 | `/.well-known/agent.json` (fleet card) | `/.well-known/agent-card.json` (product card) | — | hub | Std | n | S | P |
| 52 | `/v1/agents/…` (A2A fleet) | — (moves to `a2a.scitex.ai`) | — | hub | Int | n | S | F |
| 53 | `/oauth/*`, `/oauth/userinfo/` | stays; PKCE required, device grant, DCR (decision 8) | — | hub | Std | n | M | P |
| 54 | Git HTTP `/<owner>/<repo>.git`, SSH `:2222` | stays | — | hub | Std | n | S | F |
| 55 | (none) discovery | `GET /api/v1/operations`, `GET /api/v1/openapi.json`, `GET /api/v1/health`, `GET /api/v1/hub/changes` | `hub_changes_list` | sdk + hub | Rewrite | n | M | P |
| 56 | `/apps/console/api/{notebooks/…,execute/,command/,services/<user>/<slug>/…}` | — (never public: shell/exec) | — | hub | Int | n | S | P |

## 8.2 Hub-side leaf logic that moves to its leaf (Rule L)

| # | Current | v1 path | MCP | Owner | Mech | Brk | Eff | Pre |
|---|---|---|---|---|---|---|---|---|
| 57 | `GET /api/v1/scholar/search/` (live users; `X-SCITEX-API-KEY`) | `GET /api/v1/scholar/papers?q=` (public) | `scholar_papers_list` | scholar | Rewrite + **Facade (frozen alias)** | n | M | P |
| 58 | `GET /api/v1/scholar/info/` | `GET /api/v1/scholar/sources` (public) | `scholar_sources_list` | scholar | Rewrite+Facade | n | S | F |
| 59 | `/api/stats/calculate/` (anonymous, CSRF-exempt) | `POST /api/v1/stats/tests/{test_id}/run` (read-only) | `stats_tests_run` | stats | Rewrite; Hub copy Remove | y | M | P |
| 60 | `/api/stats/describe/` | `POST /api/v1/stats/descriptives/run` | `stats_descriptives_run` | stats | Rewrite; Remove | y | S | P |
| 61 | `/api/stats/recommend/` | `POST /api/v1/stats/tests/recommend` (read-only) | `stats_tests_recommend` | stats | Rewrite; Remove | y | S | P |
| 62 | `/api/stats/effect-size/` | `POST /api/v1/stats/effect-sizes/run` | `stats_effect_sizes_run` | stats | Rewrite; Remove | y | S | P |
| 63 | `/api/stats/posthoc/` | `POST /api/v1/stats/tests/{test_id}/run` (post-hoc test ids) | `stats_tests_run` | stats | Rewrite; Remove | y | S | P |
| 64 | `/api/stats/power/` | `POST /api/v1/stats/power-analyses/run` | `stats_power_analyses_run` | stats | Rewrite; Remove | y | S | P |
| 65 | `/api/stats/correct/` | `POST /api/v1/stats/corrections/run` | `stats_corrections_run` | stats | Rewrite; Remove | y | S | P |
| 66 | `/api/stats/flowchart/` | — (UI asset) | — | stats | Remove | y | S | P |
| 67 | `/api/stats/plot/`, `/api/plot/` | `POST /api/v1/figrecipe/figures` (202) | `figrecipe_figures_create` | figrecipe | Rewrite; Remove | y | M | P |
| 68 | `/api/docx2tex/` (anonymous) | `POST /api/v1/writer/conversions` (202) | `writer_conversions_create` | writer | Rewrite; Remove | y | S | P |
| 69 | `/api/read-image-metadata/` | `POST /api/v1/figrecipe/images/read-metadata` (read-only) | `figrecipe_images_read_metadata` | figrecipe | Rewrite; Remove | y | S | F |
| 70 | `/apps/console/api/jobs/submit/` (SLURM) | `POST /api/v1/hpc/jobs` | `hpc_jobs_create` | hpc | Rewrite (out-of-process) | n | L | P |
| 71 | `/apps/console/api/jobs/{<int>/status/,queue/}` | `GET /api/v1/hpc/jobs/{job_id}`, `GET /api/v1/hpc/jobs` | `hpc_jobs_get`, `hpc_jobs_list` | hpc | Rewrite | n | S | P |
| 72 | `/apps/console/api/jobs/<int>/cancel/` | `POST /api/v1/hpc/jobs/{job_id}/cancel` | `hpc_jobs_cancel` | hpc | Rewrite | n | S | P |
| 73 | `/apps/console/api/jobs/<int>/output/` | `GET /api/v1/hpc/job-logs/{job_id}` | `hpc_job_logs_get` | hpc | Rewrite | n | S | F |

## 8.3 Leaf UI-mount APIs (`/apps/<slug>/api/…`)

| # | Current | v1 path | MCP | Owner | Mech | Brk | Eff | Pre |
|---|---|---|---|---|---|---|---|---|
| 74 | dataset `api/datasets` GET (project files) | `GET /api/v1/dataset/project-datasets` | `dataset_project_datasets_list` | dataset | Done; legacy Int | n | S | P |
| 75 | dataset `api/register` POST | `POST /api/v1/dataset/project-datasets` | `dataset_project_datasets_create` | dataset | Done; legacy Int | n | S | P |
| 76 | dataset `api/upload` POST | `POST /api/v1/hub/uploads` | `hub_uploads_create` | hub | Rewrite; legacy Int | n | S | F |
| 77 | dataset MCP `db_search`, `*_fetch` | `GET /api/v1/dataset/datasets`, `POST …/project-datasets/{id}/fetch` | `dataset_datasets_list`, `dataset_project_datasets_fetch` | dataset | Done | n | S | P |
| 78 | (none) Clew project setup | `POST /api/v1/clew/projects` (provision store), `GET /api/v1/clew/projects/{project_id}` | `clew_projects_create`, `clew_projects_get` | clew | Rewrite | n | M | P |
| 79 | clew `api/status/`, `api/stats/` | `GET /api/v1/clew/projects/{project_id}` | `clew_projects_get` | clew | Rewrite; legacy Int | n | S | P |
| 80 | clew `api/claims/` GET; MCP `clew_list_claims`; writer `api/claims` GET | `GET /api/v1/clew/claims` | `clew_claims_list` | clew | Rewrite; writer copy Remove | n | S | P |
| 81 | MCP `clew_add_claim`; writer `api/claims` POST | `POST /api/v1/clew/claims` | `clew_claims_create` | clew | Rewrite; writer copy Remove | n | M | P |
| 82 | writer `api/claims/<id>` | `GET /api/v1/clew/claims/{claim_id}` | `clew_claims_get` | clew | Rewrite; writer copy Remove | n | S | P |
| 83 | MCP `clew_verify_claim`; clew `api/verify-chain/`; live-paper `api/claim/verify`, `api/claims/verify` | `POST /api/v1/clew/claims/{claim_id}/verify` (202) | `clew_claims_verify` | clew | Rewrite; copies Remove | n | M | P |
| 84 | clew `api/dag/{json,mermaid}/`; writer `api/claims/<id>/chain`; live-paper `api/dag` | `GET /api/v1/clew/dags/{dag_id}?format=json\|mermaid` (`dag_id` = claim id) | `clew_dags_get` | clew | Rewrite; copies Remove | n | S | P |
| 85 | clew `api/runs/`, `api/verify-run/` | `GET /api/v1/clew/runs[/{run_id}]`, `POST …/runs/{run_id}/verify` | `clew_runs_list/get/verify` | clew | Rewrite; legacy Int | n | S | F |
| 86 | clew `api/file/` | `GET /api/v1/clew/files/{file_id}` | `clew_files_get` | clew | Rewrite; legacy Int | n | S | F |
| 87 | clew `api/register/` (hash, csrf_exempt) | `POST /api/v1/clew/hashes` | `clew_hashes_create` | clew | Rewrite+Facade | n | S | P |
| 88 | clew `api/verify/<hash>/` | `GET /api/v1/clew/hashes/{hash_id}` (public) | `clew_hashes_get` | clew | Rewrite+Facade | n | S | P |
| 89 | clew `api/add-examples/` | — (demo) | — | clew | Int | n | S | F |
| 90 | clew `badge/<hash>/` (SVG) | stays (asset, not a JSON API) | — | clew | Std | n | S | F |
| 91 | writer `api/compile` (session + CSRF) | `POST /api/v1/writer/manuscripts/{manuscript_id}/compile` (202) | `writer_manuscripts_compile` | writer | Rewrite; legacy Int | n | M | P |
| 92 | writer `api/compile/status` | `GET /api/v1/writer/jobs/{job_id}` | `writer_jobs_get` | writer | Rewrite | n | S | P |
| 93 | writer `api/pdf` | `GET /api/v1/writer/manuscripts/{manuscript_id}` (`pdf_url`) | `writer_manuscripts_get` | writer | Rewrite | n | S | P |
| 94 | writer `api/bib/*` | `/api/v1/writer/bib-entries` CRUD | `writer_bib_entries_*` | writer | Rewrite; legacy Int | n | M | F |
| 95 | writer `api/figures` | `GET /api/v1/writer/figures` | `writer_figures_list` | writer | Rewrite | n | S | F |
| 96 | writer `api/project/<int>/section/<path>/` | `/api/v1/writer/sections[/{section_id}]` list/get/update | `writer_sections_*` | writer | Rewrite; legacy Int | n | M | F |
| 97 | writer `api/scholar/*` | — (use the scholar dock) | — | writer | Remove | n | S | F |
| 98 | writer other catch-all handlers, `v2/…` | — (UI) | — | writer | Int | n | S | F |
| 99 | scholar `api/search` (UI) | `GET /api/v1/scholar/papers` | `scholar_papers_list` | scholar | Rewrite; legacy Int | n | S | P |
| 100 | scholar `api/library/save` | `POST /api/v1/scholar/library-items` | `scholar_library_items_create` | scholar | Rewrite | n | S | F |
| 101 | scholar `api/library/{save-bulk,import}` | `POST /api/v1/scholar/library-items/import` (202) | `scholar_library_items_import` | scholar | Rewrite | n | S | F |
| 102 | scholar `api/library/export` | `POST /api/v1/scholar/library-items/export` (read-only, 202) | `scholar_library_items_export` | scholar | Rewrite | n | S | F |
| 103 | scholar `api/library/{enrich,pdf}` | `POST /api/v1/scholar/library-items/{library_item_id}/{enrich,fetch}` (202) | `scholar_library_items_enrich/fetch` | scholar | Rewrite | n | S | F |
| 104 | scholar `api/graph/*`, `api/graphs/*` | `/api/v1/scholar/citation-graphs` CRUD | `scholar_citation_graphs_*` | scholar | Rewrite | n | M | F |
| 105 | scholar `api/searches/*` | `/api/v1/scholar/saved-searches` CRUD | `scholar_saved_searches_*` | scholar | Rewrite | n | S | F |
| 106 | scholar remaining UI routes (≈22 of 34) | — (UI) | — | scholar | Int | n | S | F |
| 107 | figrecipe `preview`, `save`, figure handlers | `/api/v1/figrecipe/figures` get/update | `figrecipe_figures_*` | figrecipe | Rewrite | n | M | F |
| 108 | figrecipe `api/compose` | `POST /api/v1/figrecipe/figures/compose` (202) | `figrecipe_figures_compose` | figrecipe | Rewrite | n | S | F |
| 109 | figrecipe `api/chat/stream`, `stats/*_bracket`, ≈50 other handlers | — (UI) | — | figrecipe | Int | n | S | F |
| 110 | stats `api/run` | `POST /api/v1/stats/tests/{test_id}/run` | `stats_tests_run` | stats | Rewrite; legacy Int | n | S | P |
| 111 | stats `api/run-all` | `POST /api/v1/stats/test-batches` (202) | `stats_test_batches_create` | stats | Rewrite | n | S | F |
| 112 | stats `api/{recommend,recommend-test}`, `api/public/recommend` (anonymous) | `POST /api/v1/stats/tests/recommend` | `stats_tests_recommend` | stats | Rewrite; anonymous copy Remove | y | S | P |
| 113 | stats `api/{describe,effect-size,power,posthoc,correct}` | as #60–#65 | as #60–#65 | stats | Rewrite; legacy Int | n | S | F |
| 114 | stats `api/plot` | `POST /api/v1/figrecipe/figures` | `figrecipe_figures_create` | figrecipe | Remove | n | S | F |
| 115 | stats `api/report/pdf` | `POST /api/v1/stats/reports` (202) | `stats_reports_create` | stats | Rewrite | n | S | F |
| 116 | stats `api/tests` GET | `GET /api/v1/stats/tests[/{test_id}]` | `stats_tests_list/get` | stats | Rewrite | n | S | P |
| 117 | (none) Live Paper publish | `POST /api/v1/live-paper/papers` (202), `GET …/papers[/{paper_id}]` | `live_paper_papers_create/list/get` | live-paper | Rewrite | n | M | P |
| 118 | live-paper `api/{bundle-info,pdf}` | `GET /api/v1/live-paper/papers/{paper_id}` | `live_paper_papers_get` | live-paper | Rewrite; legacy Int | n | S | P |
| 119 | live-paper `api/ping` | `GET /api/v1/health` | — | live-paper | Remove | n | S | F |
| 120 | live-paper `api/claims`, `api/dag` | the clew dock (#80, #84) | — | live-paper | Remove (reads clew) | n | S | F |
| 121 | live-paper `api/event-log` | `GET /api/v1/live-paper/events` | `live_paper_events_list` | live-paper | Rewrite | n | S | F |
| 122 | live-paper `api/comments` | `/api/v1/live-paper/comments` CRUD | `live_paper_comments_*` | live-paper | Rewrite | n | S | F |
| 123 | live-paper `api/dashboard`, `doi/<path>/` | — (UI / public HTML resolver) | — | live-paper | Int | n | S | F |

## 8.4 MCP tools (local servers and the umbrella)

| # | Current | v1 name | Owner | Mech | Brk | Eff | Pre |
|---|---|---|---|---|---|---|---|
| 124 | clew: 29 tools `clew_<verb>_<noun>` | derived `clew_<resource>_<verb>` for #78–#88; tools without a REST twin stay local-only; old names kept as aliases for one minor | clew | Rewrite | y | M | P |
| 125 | writer: 59 `writer_*` + stray `get_usage` | derived for #91–#96; `get_usage` → `writer_skills_get` (§5 pair) | writer | Rewrite | y | M | P |
| 126 | scholar: 26 `scholar_*` + legacy unprefixed server (the default for `mcp start`) | derived for #57, #99–#105; legacy server Remove | scholar | Rewrite+Remove | y | M | P |
| 127 | dataset: 27 unprefixed (`db_search`, `*_fetch`, `skills_*`) | 9 derived `dataset_*` (done); remaining local tools keep §2 names until migrated | dataset | Done | n | S | P |
| 128 | figrecipe: 98 (`plt_*`, `fr_*`, `colors_*`, `diagram_*`) | derived `figrecipe_*` for #67, #69, #107–#108; `plt_*` stays the local plotting API | figrecipe | Rewrite | y | L | F |
| 129 | stats: 18 unprefixed (`run_test`, `describe`, …) | derived `stats_*` for #59–#65, #110–#116 | stats | Rewrite | y | M | P |
| 130 | live-paper: 9 `live_paper_*`, no publish | derived `live_paper_*` for #117–#122 | live-paper | Rewrite | y | S | P |
| 131 | hpc: 15 unprefixed (`submit_sbatch`, `compute_submit`, …) | derived `hpc_jobs_*`, `hpc_job_logs_get` | hpc | Rewrite | y | M | P |
| 132 | sdk: `app_*` 11, `ui_*` 6 | local-only developer tools | sdk | Int | n | S | F |
| 133 | umbrella `scitex mcp start`: 617 tools, ≈238 double-prefixed (`clew_clew_*`, `scholar_scholar_*`, `writer_writer_*`, `io_io_*`, `app_app_*`) | mounts derived tools unchanged (API-T003), so the double prefixes disappear | scitex-python | Rewrite | y | M | P |
| 134 | umbrella `cloud_*` / `hub_*` (56 duplicated) | duplicates removed; `hub_*` = derived from the `hub` dock only | scitex-python | Remove | y | S | P |
| 135 | umbrella `plt_*` (112) overlapping `figrecipe_*` (98) | one namespace per distribution | scitex-python, figrecipe | Remove | y | S | F |

## 8.5 Enabling SDK/Hub work (not endpoint rows)

| # | Item | Rule | Owner | Eff | Pre |
|---|---|---|---|---|---|
| E1 | Rule ids on `ApiPluginContractError` (`rule` attribute and message prefix) | all D | sdk | S | P |
| E2 | `public=True` on `ApiOperation`; anonymous caller path in `api_serve` | API-A004 | sdk | S | P |
| E3 | `contract="1"`, `CONTRACT_MAJOR`, host refusal, `REFUSED` → `hub/docks` | API-D003 | sdk + hub | S | P |
| E4 | `Location` on 201; object `id` check; fixed Job helper | API-V001, F005, J001 | sdk | S | P |
| E5 | snake_case field/enum check; `max_limit ≤ 200`; id charset; reserved names | API-F001, G001, F004, R006 | sdk | S | P |
| E6 | `scitex_sdk.testing.api_contract`, sharing the inventory module | 02 §5 | sdk | M | P |
| E7 | `PS-SDK-API` source rule; scitex-dev §2 delegation for derived tools | API-T001, V003 | sdk + dev | S | P |
| E8 | Aggregation function + `api list` + `GET /api/v1/operations` (inventory owner) | API-D008, R006 | sdk + hub | M | P |
| E9 | Merged OpenAPI `/api/v1/openapi.json` + Redoc page | API-O001/O002 | sdk + hub | M | P |
| E10 | Remote MCP `/api/v1/mcp` from admitted docks, scope-filtered, OAuth protected-resource metadata | API-T004 | sdk + hub | M | P |
| E11 | Out-of-process docking: `scitex-sdk api serve`, `api_proxy.forward`, `dock_token_caller`, `/_dock/{descriptor,health,ready}` | API-D009 | sdk | L | F (needed by #70) |
| E12 | `RateLimit*` headers in the Hub limiter; `Deprecation`/`Sunset` middleware for allowlisted legacy routes | API-H002/H003 | hub | S | P |
| E13 | Hub legacy allowlist test (`test_api_surface.py`) | API-D004 | hub | S | P |
| E14 | The `hub` dock plugin (rows #3–#55) | all | hub | L | P |
| E15 | Fold `scitex_hub.apps`/`app_config` into `scitex.apps`; one dock record with UI + API facets | 02 §3.7 | hub + sdk | M | F |
| E16 | `exposure` ceiling + privileged scope suffix; per-call cost measurement and `cost_class_exceeded` flags; `SCITEX_API_PUBLIC_TIER` config; priority classes (`SciTeX-Priority-Class`, Job `priority_class`/`queued_seconds`) | API-K001–K008, Q001–Q003, M002 | sdk + hub | M | P |
| E17 | `public_compute` sponsored usage kind on the #1256 promotion account (budget, 50/80/100 % alerts, backstop, degradation), in shadow mode | API-K005–K007 | hub (spend_app) | M | P (shadow) |
| E18 | Public sandboxed compile pool (no network, read-only, 2 slots) for `writer.manuscripts.compile` | 06 §12.4 | writer + infra | M | P |
| E19 | Hosted MCP fixes: problem object in `isError` results, `_meta.request_id`, `tools/list` scope filtering, `/.well-known/mcp.json`, OAuth protected-resource metadata | API-M001–M006 | sdk + hub | M | P |

## 8.6 Counts

The counts cover rows #1–#135 (endpoints and tools) and leave out E1–E15. They were produced by
parsing this file's table columns rather than by hand.

| | Rows |
|---|---|
| Total endpoint/tool rows | **135** |
| Breaking for an existing caller (Brk = y) | **26** (16 REST rows; 10 local-MCP rows) |
| Must land before beta (Pre = P) | **68** (21 of them breaking) |
| Already v1 (Done) | 4 (dataset #74, #75, #77, #127) |
| Internal-only (Int, Int+Rewrite, Int→Rewrite) | 20 |
| Standards-defined (Std) | 7 |
| Remove with no v1 twin | 15 |
| Rewrite and/or Facade | 89 |

**Breaking rows with external callers today:**

- #1, #2: CLI JWT;
- #4: CLI mint;
- #50: operator `/mcp`;
- the anonymous Hub stats/plot/docx2tex calls (#59–#69, #112). Prod logs show no named external
  client for these (audit §6), and they are an abuse surface.

The one public endpoint with real users, scholar search (#57), keeps its exact path as a frozen
facade and is **not** breaking. The 10 MCP rows break only local stdio tool names, and each keeps
its old name as an alias for one minor release.
