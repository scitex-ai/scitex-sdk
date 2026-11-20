---
name: package-navigation
description: |
  [WHAT] Project shared package hierarchy metadata into navigation trees and breadcrumbs.
  [WHEN] Use when an app or host needs stable package indices without maintaining its own ecosystem inventory.
  [HOW] Supply package identities to scitex_sdk.app.package_navigation.build_package_navigation; Dev discovers and validates the owning providers.
tags: [scitex-app-navigation]
---

# Package navigation

`scitex_sdk.app.package_navigation.build_package_navigation(distributions)`
returns selected packages, pruned trees, stable indices and breadcrumbs. The
input is a finite collection of distribution identities from the caller's
actual catalog. The function normalizes and deduplicates them; it does not
infer installation, enablement, project scope or live availability.

Dev owns `scitex_dev.hierarchy` discovery and schema validation. Providers own
the inert allocations. The SDK owns the display projection; the host supplies
routes. Do not copy the umbrella package list into an app, assign indices from
installation order, or turn missing metadata into an invented hierarchy.

Each package row has `distribution`, `state` (`indexed` or `unindexed`),
`node_id`, `root_id`, `index`, and `breadcrumbs`. Unindexed rows have null
identity/index fields and empty breadcrumbs. `trees` retains only selected
packages and their ancestors, in numeric index order. The result also includes
`unindexed`, `schema_version=1`, `declarations_only=true`, `live_verified=false`.
These are navigation declarations, never route admission or availability.

This capability requires Dev's new hierarchy discovery API; older declared
Dev floors do not imply support. Missing support raises
`PackageNavigationUnavailable`. Invalid/conflicting metadata propagates its
validation/read error. Hosts should report unavailable/invalid explicitly,
keeping existing document routes readable without inventing fallback indices.
The optional `metadata_path` restricts metadata discovery only; resource lookup
uses normal interpreter import paths. Do not expose arbitrary paths in a host
request parameter.

Source: `app/package_navigation.py`. Owning behavioral controls:
`tests/scitex_sdk/app/test_package_navigation.py`, using real metadata and a
provider that raises if imported. SDK source or wheel acceptance does not
qualify the umbrella artifact, hosted integration or global search. This helper
is an application composition primitive; it does not add a CLI/MCP operation or
serve a Web API. Hosts expose their composed catalog through their own routes.
