"""Shared navigation projection of Dev-owned inert hierarchy catalogs.

The SDK builds display trees and breadcrumbs; Dev validates declarations and
Root/leaf providers own allocations. Hosts supply package identities and URLs
separately. This module neither loads leaf code nor checks live availability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

__all__ = ["PackageNavigationUnavailable", "build_package_navigation"]


class PackageNavigationUnavailable(RuntimeError):
    """The installed Dev does not provide the hierarchy discovery contract."""


def build_package_navigation(
    distributions: Iterable[str], *, metadata_path: Sequence[str | Path] | None = None
) -> dict:
    """Project selected package identities into shared trees and breadcrumbs.

    Requires Dev's ``list_package_hierarchies`` and normalization APIs. Missing
    support raises PackageNavigationUnavailable; invalid declarations retain
    their discovery error. An available but empty catalog leaves every selected
    package explicitly unindexed, without inventing indices or parent groups.

    ``metadata_path`` restricts distribution metadata discovery, not resource
    lookup. Normal interpreter import paths locate declared inert JSON files.
    No URL, installation/enablement claim or project/user scope is inferred.
    """
    try:
        from scitex_dev import list_package_hierarchies, normalize_distribution_name
    except ImportError as error:
        raise PackageNavigationUnavailable(
            "Installed scitex-dev lacks package hierarchy discovery support"
        ) from error

    owners = sorted({normalize_distribution_name(name) for name in distributions})
    catalogs = list_package_hierarchies(path=metadata_path)
    positions = {}
    trees = []
    for catalog in catalogs:
        nodes = {node.id: node for node in catalog.nodes}
        visible = set()
        for node in catalog.nodes:
            if node.distribution not in owners:
                continue
            path = []
            current = node
            while current is not None:
                visible.add(current.id)
                path.append({"id": current.id, "index": current.index,
                             "label": current.label, "kind": current.kind})
                current = nodes[current.parent_id] if current.parent_id is not None else None
            positions[node.distribution] = {
                "distribution": node.distribution,
                "state": "indexed", "node_id": node.id,
                "root_id": catalog.root, "index": node.index,
                "breadcrumbs": list(reversed(path)),
            }
        children = {}
        for node in catalog.nodes:
            if node.id in visible:
                children.setdefault(node.parent_id, []).append(node)

        def branch(node):
            return {
                "id": node.id, "index": node.index, "label": node.label,
                "kind": node.kind, "distribution": node.distribution,
                "children": [branch(child) for child in children.get(node.id, ())],
            }

        if visible:
            trees.append(branch(nodes[catalog.root]))
    packages = [positions.get(owner, {
        "distribution": owner, "state": "unindexed", "node_id": None,
        "root_id": None, "index": None, "breadcrumbs": [],
    }) for owner in owners]
    packages.sort(key=lambda row: (
        row["state"] != "indexed", row["root_id"] or "",
        tuple(map(int, row["index"].split("."))) if row["index"] else (),
        row["distribution"],
    ))
    return {
        "schema_version": 1, "trees": trees, "packages": packages,
        "unindexed": [row["distribution"] for row in packages if row["state"] == "unindexed"],
        "declarations_only": True, "live_verified": False,
    }
