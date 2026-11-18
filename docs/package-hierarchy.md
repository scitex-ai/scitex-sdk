# Package hierarchy contract

`scitex_sdk.hierarchy` supplies immutable `HierarchyNode` records, complete-tree
validation, numeric ordering and root-to-node breadcrumbs for shared navigation
and search. The owning source is
[`hierarchy/__init__.py`](../src/scitex_sdk/hierarchy/__init__.py); the behavioral
checks are in
[`test___init__.py`](../tests/scitex_sdk/hierarchy/test___init__.py).

Package identity, hierarchy index and display label are distinct. Canonical
package identities use `package:<distribution>`; display labels can change
without changing the identity or index. Indices are positive dotted integers,
except the SciTeX root at `0`. Numeric ordering places `4.2` before `4.10`.
Discovery order never allocates or renumbers indices. Missing packages are not
silently assigned a slot.

The umbrella owns the root and layer declarations. Each leaf owns only its own
allocation. The SDK declares `package:scitex-sdk`, index `2.5`, parent
`scitex.applications`, through the `scitex_dev.hierarchy` entry-point group:
`scitex-sdk = scitex_sdk.hierarchy:get_hierarchy_nodes`.

```python
from scitex_sdk.hierarchy import (
    HierarchyNode, get_hierarchy_nodes, hierarchy_breadcrumbs,
)

# An explicit standalone fixture. Production parents belong to the umbrella.
nodes = (
    HierarchyNode("scitex", "0", "SciTeX", None),
    HierarchyNode("scitex.applications", "2", "Applications", "scitex"),
    *get_hierarchy_nodes(),
)
path = hierarchy_breadcrumbs(nodes, "package:scitex-sdk")
assert [node.label for node in path] == ["SciTeX", "Applications", "SciTeX SDK"]
```

`validate_hierarchy(nodes)` accepts an iterable and returns records in stable
numeric index order. It rejects empty or ambiguously rooted trees, duplicate
identities or indices, missing ancestors, cycles, and a child index that does
not extend its actual parent's index by exactly one component. The root's
direct children use one-component indices (`1`, `2`, etc.). A malformed node
raises `ValueError`; an untyped provider record raises `TypeError`. An unknown
breadcrumb identity raises `KeyError`. A leaf declaration alone is incomplete
and cannot pass complete-tree validation without its parents.

This entry point is a declaration for the shared contract. Automatic Dev
hierarchy discovery/validation and the umbrella's root/layer provider are not
implemented by this change. The other proposal allocations must remain owned
by their leaves; the SDK does not maintain a second inventory of all packages.
Docs ordering, global search, all installed application adoption and hosted
breadcrumbs are not enabled merely by installing this declaration.

This is a public navigation taxonomy, not a dependency graph, permission grant,
project scope or proof of live availability. Hosts must enforce access and
escape labels when rendering them. Existing document identities and links are
unchanged. No API here opens documents, imports discovered leaf providers,
assigns unlisted indices or changes a service.

## Bind records to their declaring package

Before composing a tree, call `validate_hierarchy_provider(nodes,
distribution=owner)` for each explicitly selected declaration. `owner` is the
canonical owning distribution from the caller's metadata/admission process.
The SDK does not discover, import or authenticate that provider for you.

```python
from scitex_sdk.hierarchy import get_hierarchy_nodes, validate_hierarchy_provider

owned = validate_hierarchy_provider(
    get_hierarchy_nodes(), distribution="scitex-sdk"
)
assert [node.distribution for node in owned] == ["scitex-sdk"]
```

A provider must declare its own package node and cannot claim another
package's record. Only the umbrella distribution `scitex` may include root or
group records without a distribution. Empty declarations, duplicate IDs or
indices, noncanonical owner names and untyped rows fail explicitly. The result
is an immutable tuple of the original records in numeric index order; missing
parents are permitted at this partial-declaration stage. A group-only umbrella
declaration is not a substitute for its own package record.

This ownership check does not verify allocated index values against an external
inventory, prove code provenance, authorize provider execution or grant access.
After checking each provider, combine the selected records and call
`validate_hierarchy` to check the complete tree, including missing parents and
cross-provider duplicate IDs/indices. Neither function enables hosted search
or replaces the host's admission and permission checks. Behavioral controls
for this boundary live in
[`test___init___provider_ownership.py`](../tests/scitex_sdk/hierarchy/test___init___provider_ownership.py).
