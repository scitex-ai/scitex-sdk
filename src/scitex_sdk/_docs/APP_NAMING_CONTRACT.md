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

Operator label decisions (2026-10-20, binding): `SciTeX Storage`,
`SciTeX Scholar`, `SciTeX Stats` — App lane executes (manifest + hub
tiles). The SDK App itself carries the operator-ruled short label `SDK`
— a RECORDED EXCEPTION, not drift, so the family-form advisory below
will flag it by design; do not "fix" the SDK manifest to silence it.

## Rules

1. `slug`: `[a-z0-9]+(-[a-z0-9]+)*`, and it IS the mount leaf —
   the leaf serves at `/apps/<slug>/`. Missing/malformed slug is a
   validator ERROR. A published slug is immutable: renaming the mount
   means a new slug plus a hub-side redirect (App lane), never a silent
   move. Rationale: the slug is the only name that appears in URLs,
   and URLs are a published contract.
2. `label`: user-facing tile/product name, family form `SciTeX <Name>`
   (writer, SDK App). Bare labels (Storage, Scholar, Stats) are
   grandfathered drift, not the pattern. Non-family labels are a
   validator ADVISORY (warning, never a failure) — see the scholar
   `_editor` lesson in `_validate/_manifest.py` for why taste is not
   gated as errors.
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

## Approval flow

- New leaf / new name: App lane proposes in the leaf PR (manifest);
  the SDK validator gates the mechanical rules automatically.
- Advisory drift (label form, name suffix): reviewed at PR time by the
  SDK lane on request; warnings never block.
- Published-slug rename: App-lane PR with redirect + SDK-lane ack on
  the contract doc.
- New/changed contract fields (schema, mount policy, scopes): SDK-lane
  PR here first; leaves adopt after release.
