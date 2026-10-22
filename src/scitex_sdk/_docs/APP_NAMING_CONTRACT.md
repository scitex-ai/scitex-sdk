# App naming contract (DRAFT v1 — pending App-lane approval)

The SDK lane owns this surface: manifest schema, the validator, the mount
contract, STARTERS. The App lane owns leaf names, hub mounts/redirects,
tiles. Neither renames across the boundary unilaterally.

Measured base (2026-10-20): storage (`storage_app`/slug `storage`/label
`Storage`), scholar (`scholar_editor`/`scholar`/`Scholar` — `_editor`
because `scholar_app` collides in hub's registry), writer
(`writer_app`/`writer`/`SciTeX Writer`), stats
(`stats_calculator`/`stats`/`Stats`), SDK App (`app_creator_app`/slug
`create-app`/label `SDK`, mount `/apps/sdk/` prepared).

Operator label decisions (2026-10-20, SUPERSEDED 2026-10-23): `SciTeX Storage`,
`SciTeX Scholar`, `SciTeX Stats` — App lane executed (manifest + hub
tiles). The SDK App itself carries the operator-ruled short label `SDK`
— a RECORDED EXCEPTION, not drift.

Operator tile-label decision (2026-10-23, CURRENT): the launcher page carries
the family brand, so tiles read short — `Cards`, `Agent Container`,
`Storage`, `Scholar`, `Stats`, `FigRecipe`, `Writer`. The `SciTeX ` prefix on
a tile is drift (validator ADVISORY, never a failure). Tab/in-app header
titles keep the `SciTeX <Tool>` form (`ui/branding.py shell_title`) — tile
label and header title are independent strings, and that separation is
intended. Agent-container keeps its single FOUNDATION tile; the WORK duplicate
(`SciTeX Agent Container App`) is dropped. Leaf value edits + hub launcher
entries are App-lane execution; this contract only gates the mechanics.

## Rules

1. `slug`: `[a-z0-9]+(-[a-z0-9]+)*`, and it IS the mount leaf —
   the leaf serves at `/apps/<slug>/`. Missing/malformed slug is a
   validator ERROR. A published slug is immutable: renaming the mount
   means a new slug plus a hub-side redirect (App lane), never a silent
   move. Rationale: the slug is the only name that appears in URLs,
   and URLs are a published contract.
2. `label`: user-facing tile name, SHORT form (operator 2026-10-23) —
   `Cards`, `Agent Container`, `Storage`, `Scholar`, `Stats`, `FigRecipe`,
   `Writer`. The launcher page carries the family brand, so a `SciTeX `
   prefix on a tile is drift: validator ADVISORY (warning, never a
   failure). Tile label and in-app header title are INDEPENDENT strings —
   headers keep the `SciTeX <Tool>` form (`ui/branding.py shell_title`).
3. `name`: advisory `_app`/`-app` suffix (existing advisory, unchanged).
   Django `AppConfig.label` stays fully namespaced and unique
   (`scitex_storage_django` pattern) — the hub collision bug is the
   reason; never shorten it to match the manifest name.
4. `pip_package`: the dist name; SOLE source of the version. A
   hand-written manifest `version` is a validator ERROR (existing rule).
5. Mount namespace (`app_name`) is stable per leaf. One mount path per
   namespace — mounting the same app at two paths breaks `{% url %}`
   reverse; a second path is a redirect, not a second mount (App lane).
6. Tile icon: the leaf manifest `icon` is the SOLE source. Hosts render
   it, never substitute a hardcoded glyph — a tile showing something
   other than the manifest icon is a host bug, not leaf debt.
   (Operator 2026-10-20: all applications, leaf owns icons. Hub's
   `launcher_links/*.json` hardcodes — chat, create-app, settings — are
   App-lane debt to align with the leaf manifests.)
7. Favicon (operator 2026-10-20: drift intolerable). Single canonical
   mark: `scitex_sdk/ui/img/scitex-favicon.svg` (the SciTeX snake),
   served via the shared `_branding_head.html` partial (or the shell,
   which includes it) — never a leaf-local `<link rel="icon">`.
   Per-platform PNG set (generated from the SVG, same pixels):
   16 + 32 (classic tab), 180 (apple-touch-icon), 192 + 512 (PWA
   manifest), at `scitex_sdk/ui/img/favicon-{16,32,180,192,512}.png`.
   Leaf-local favicon files (`favicon*.png`, PWA icon copies) and
   hand-rolled data-URI views (`_favicon.py` pattern) are validator
   ADVISORIES to migrate; App lane deletes the copies and points PWA
   manifests at the SDK paths.
8. `group`: leaf-declared launcher section (operator 2026-10-23) —
   `foundation` | `work` | `publication`, lowercase canonical, matched
   case-insensitively (same convention as `scope`). OPTIONAL: omitted
   means undeclared and the host keeps its existing grouping, so adoption
   is per-leaf. A typo'd value is a validator ERROR. Read at runtime via
   `ScitexAppConfig.app_group` (`None` = undeclared). One tile per leaf:
   the same app in two sections is a host duplicate, not a second
   declaration (App lane).

## Approval flow

- New leaf / new name: App lane proposes in the leaf PR (manifest);
  the SDK validator gates the mechanical rules automatically.
- Advisory drift (label form, name suffix): reviewed at PR time by the
  SDK lane on request; warnings never block.
- Published-slug rename: App-lane PR with redirect + SDK-lane ack on
  the contract doc.
- New/changed contract fields (schema, mount policy, scopes): SDK-lane
  PR here first; leaves adopt after release.
