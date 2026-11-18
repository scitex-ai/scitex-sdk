"""Stable, leaf-owned package hierarchy records for navigation and search.

This contract describes public taxonomy, not dependencies, permissions or live
availability. Dev discovers providers; hosts render only their admitted scope.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "HierarchyNode",
    "get_hierarchy_nodes",
    "hierarchy_breadcrumbs",
    "validate_hierarchy",
    "validate_hierarchy_provider",
]


def _text(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError(
            f"hierarchy {field} must be nonempty text without control characters"
        )


def _distribution(value: str) -> None:
    _text(value, "distribution")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is None:
        raise ValueError("hierarchy distribution must use canonical spelling")


@dataclass(frozen=True)
class HierarchyNode:
    """One stable identity/index declared by its owning package.

    Distribution names use canonical lowercase hyphenated spelling. Package
    node IDs are ``package:<distribution>``; root/group IDs have no distribution.
    Indices are numeric dotted strings, independent of discovery order.
    """

    id: str
    index: str
    label: str
    parent_id: str | None
    distribution: str | None = None

    def __post_init__(self) -> None:
        for field in ("id", "index", "label"):
            _text(getattr(self, field), field)
        if re.fullmatch(r"(?:0|[1-9][0-9]*(?:\.[1-9][0-9]*)*)", self.index) is None:
            raise ValueError("hierarchy index must be 0 or positive dotted integers")
        if self.parent_id is not None:
            _text(self.parent_id, "parent_id")
        if self.distribution is not None:
            _distribution(self.distribution)
            if self.id != f"package:{self.distribution}":
                raise ValueError("hierarchy package id must match its distribution")
        elif self.id.startswith("package:"):
            raise ValueError("hierarchy package nodes need a distribution")


def _records(
    nodes: Iterable[HierarchyNode],
) -> tuple[tuple[HierarchyNode, ...], dict[str, HierarchyNode]]:
    rows = tuple(nodes)
    by_id: dict[str, HierarchyNode] = {}
    indices: set[str] = set()
    for node in rows:
        if not isinstance(node, HierarchyNode):
            raise TypeError("hierarchy providers must return HierarchyNode records")
        if node.id in by_id:
            raise ValueError(f"duplicate hierarchy id: {node.id}")
        if node.index in indices:
            raise ValueError(f"duplicate hierarchy index: {node.index}")
        by_id[node.id] = node
        indices.add(node.index)
    return rows, by_id


def _ordered(nodes: Iterable[HierarchyNode]) -> tuple[HierarchyNode, ...]:
    return tuple(sorted(nodes, key=lambda node: tuple(map(int, node.index.split(".")))))


def validate_hierarchy_provider(
    nodes: Iterable[HierarchyNode], *, distribution: str
) -> tuple[HierarchyNode, ...]:
    """Check one provider's record ownership before composing a complete tree.

    The canonical owning distribution must declare its own package node and
    cannot declare another distribution's package. Only the umbrella ``scitex``
    may declare root/group records without a distribution. Duplicate IDs or
    indices and untyped rows fail. Return stable numeric index order.

    This checks a partial declaration, not ancestors or complete-tree integrity.
    It neither discovers/imports providers nor proves code provenance, allocated
    indices, host admission, permission or live availability. Compose admitted
    declarations and call ``validate_hierarchy`` separately.
    """
    _distribution(distribution)
    rows, _ = _records(nodes)
    for node in rows:
        if node.distribution is None:
            if distribution != "scitex":
                raise ValueError(f"hierarchy groups belong to scitex: {node.id}")
        elif node.distribution != distribution:
            raise ValueError(
                f"hierarchy provider {distribution} cannot declare {node.distribution}"
            )
    if not any(node.distribution == distribution for node in rows):
        raise ValueError(
            f"hierarchy provider must declare its own package: {distribution}"
        )
    return _ordered(rows)


def validate_hierarchy(nodes: Iterable[HierarchyNode]) -> tuple[HierarchyNode, ...]:
    """Validate a complete declared tree and return stable numeric index order.

    A nonempty tree has one ``scitex`` root at index ``0``. Root children have
    one index component; each deeper child's index extends its parent's by one
    component. Duplicate identities/indices, absent parents and cycles fail.
    Unknown or uninstalled packages are never assigned synthetic indices.
    """
    rows, by_id = _records(nodes)
    roots = [node for node in rows if node.parent_id is None]
    if len(roots) != 1 or roots[0].id != "scitex" or roots[0].index != "0":
        raise ValueError("hierarchy needs one scitex root at index 0")
    for node in rows:
        if node.parent_id is not None and node.parent_id not in by_id:
            raise ValueError(f"missing hierarchy parent: {node.parent_id}")
    for node in rows:
        seen: set[str] = set()
        current = node
        while current.parent_id is not None:
            if current.id in seen:
                raise ValueError(f"hierarchy cycle at: {current.id}")
            seen.add(current.id)
            current = by_id[current.parent_id]
    for node in rows:
        if node.parent_id is None:
            continue
        parent = by_id[node.parent_id]
        parts = node.index.split(".")
        expected = [] if parent.parent_id is None else parent.index.split(".")
        if len(parts) != len(expected) + 1 or parts[:-1] != expected:
            raise ValueError(f"hierarchy index does not extend parent: {node.id}")
    return _ordered(rows)


def hierarchy_breadcrumbs(
    nodes: Iterable[HierarchyNode], node_id: str
) -> tuple[HierarchyNode, ...]:
    """Return root-to-node records from a validated complete tree.

    An unknown identity raises KeyError rather than inventing a package or link.
    """
    by_id = {node.id: node for node in validate_hierarchy(nodes)}
    current = by_id[node_id]
    path = [current]
    while current.parent_id is not None:
        current = by_id[current.parent_id]
        path.append(current)
    return tuple(reversed(path))


def get_hierarchy_nodes() -> tuple[HierarchyNode, ...]:
    """Declare only the SDK's own allocation from the operator taxonomy.

    The umbrella owns root/layer declarations. This isolated declaration must
    be combined with those parents before complete-tree validation can succeed.
    """
    return (
        HierarchyNode(
            id="package:scitex-sdk",
            index="2.5",
            label="SciTeX SDK",
            parent_id="scitex.applications",
            distribution="scitex-sdk",
        ),
    )
