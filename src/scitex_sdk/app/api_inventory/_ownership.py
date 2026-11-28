#!/usr/bin/env python3
"""Who owns a view, and which leaf packages a hub view's code calls into.

Owner = the distribution that ships the view's module (``apps.*`` and
``config.*`` are the hub's source tree). For hub-owned views,
:func:`delegates_to` lists the leaf modules the view's OWN source references
(names bound by the module's imports, plus imports inside the view), so a
module that imports a leaf for one view does not taint its siblings.
"""

from __future__ import annotations

import ast
import importlib.metadata
import sys
from functools import cache, lru_cache

from ._view_auth import source, view_target

HUB_TOP_LEVEL = ("apps", "config", "scitex_hub", "scitex_cloud")
#: Ecosystem packages that are infrastructure, not leaf logic (N11 ignores them).
INFRA_PACKAGES = frozenset(
    {
        "scitex_sdk",
        "scitex_config",
        "scitex_logging",
        "scitex_hub",
        "scitex_cloud",
        "scitex_dev",
    }
)
ECOSYSTEM_EXTRA = frozenset(
    {"figrecipe", "socialia", "crossref-local", "openalex-local"}
)


@cache
def packages_distributions() -> dict:
    return importlib.metadata.packages_distributions()


def is_ecosystem(dist: str) -> bool:
    return dist.startswith("scitex") or dist in ECOSYSTEM_EXTRA


def owner_of(module: str | None, host_packages=HUB_TOP_LEVEL) -> tuple[str, str]:
    """``(owner_package, owner_kind)``; kind is hub, sdk, leaf or third-party.

    ``host_packages`` are the host's own top-level source packages (the hub
    checkout's ``apps``/``config``), which no distribution metadata names.
    """
    if not module:
        return "unknown", "unknown"
    top = module.split(".")[0]
    if top in host_packages:
        return "scitex-hub", "hub"
    if top == "scitex_sdk":
        return "scitex-sdk", "sdk"
    dists = packages_distributions().get(top) or []
    dist = dists[0] if dists else top
    if dist in ("scitex-hub", "scitex-cloud"):
        return dist, "hub"
    if dist == "scitex-sdk":
        return dist, "sdk"
    if is_ecosystem(dist):
        return dist, "leaf"
    return dist, "third-party"


def leaf_module(name: str) -> str | None:
    """``scitex_stats.x`` -> ``scitex_stats``; ``scitex.stats`` -> itself."""
    top = name.split(".")[0]
    if top in INFRA_PACKAGES or top in HUB_TOP_LEVEL:
        return None
    if top == "scitex":
        parts = name.split(".")
        sub = parts[1] if len(parts) > 1 else ""
        if not sub or sub.startswith("_") or sub in ("logging", "config"):
            return None
        return f"scitex.{sub}"
    dists = packages_distributions().get(top) or []
    if (
        dists
        and is_ecosystem(dists[0])
        and dists[0] not in ("scitex-hub", "scitex-sdk")
    ):
        return top
    return None


@cache
def _module_leaf_aliases(module_name: str) -> dict:
    """alias -> leaf module, for every leaf import in a module's source."""
    module = sys.modules.get(module_name)
    src = source(module) if module else ""
    try:
        tree = ast.parse(src) if src else None
    except SyntaxError:
        tree = None
    aliases = {}
    for node in ast.walk(tree) if tree is not None else ():
        if isinstance(node, ast.Import):
            for a in node.names:
                aliases[(a.asname or a.name).split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
    return {k: v for k, v in aliases.items() if leaf_module(v)}


def delegates_to(callback) -> list[str]:
    """Leaf packages a hub-owned view's own code references."""
    _, target = view_target(callback)
    module = getattr(target, "__module__", None)
    src = source(target)
    if not module or not src:
        return []
    aliases = _module_leaf_aliases(module)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in aliases:
            used.add(leaf_module(aliases[node.id]))
        elif isinstance(node, ast.Import):
            used |= {leaf_module(a.name) for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            used.add(leaf_module(node.module))
    return sorted(u for u in used if u)


__all__ = ["delegates_to", "is_ecosystem", "leaf_module", "owner_of"]
