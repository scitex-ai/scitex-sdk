#!/usr/bin/env python3
"""The tools of an aggregating (hosted) FastMCP server, attributed to owners.

An aggregator (the umbrella ``scitex.mcp_server`` behind the hub's ``/mcp``)
mounts each package's server under a namespace. This module lists the
aggregate's tools and, for each, finds the mounted peer server that provides
it, so every hosted tool row carries its namespace, its name inside the peer
(``raw_name``) and the owning distribution — the data the double-prefix
(``clew_clew_*``) and REST<->MCP findings need.
"""

from __future__ import annotations

from ._ownership import owner_of
from ._package import input_summary, list_tools, tool_owner
from ._rules import mcp_name_rules


def _peer_servers(server) -> list:
    """FastMCP servers mounted into ``server`` (fastmcp 2 and 3 layouts)."""
    peers = []
    for provider in getattr(server, "providers", None) or ():
        inner = getattr(provider, "_inner", provider)
        peer = getattr(inner, "server", None)
        if peer is not None and peer is not server:
            peers.append(peer)
    manager = getattr(server, "_tool_manager", None)
    for mounted in getattr(manager, "_mounted_servers", None) or ():
        peer = getattr(mounted, "server", None)
        if peer is not None:
            peers.append(peer)
    return peers


def _peer_index(server) -> dict:
    """raw tool name -> list of (peer distribution, peer name, tool)."""
    index: dict = {}
    for peer in _peer_servers(server):
        try:
            tools = list_tools(peer)
        except Exception:  # one broken peer must not hide the others
            continue
        modules = [tool_owner(t) for t in tools if tool_owner(t)]
        dist = owner_of(modules[0])[0] if modules else getattr(peer, "name", "unknown")
        for tool in tools:
            index.setdefault(tool.name, []).append(
                (dist, getattr(peer, "name", None), tool)
            )
    return index


def attribute(name: str, index: dict) -> tuple:
    """``(namespace, raw_name, owner)`` of a hosted tool name."""
    best = None
    for raw, providers in index.items():
        if name == raw or name.endswith("_" + raw):
            if best is None or len(raw) > len(best[0]):
                best = (raw, providers)
    if best is None:
        return None, name, None
    raw, providers = best
    namespace = name[: -len(raw) - 1] if name != raw else None
    return namespace, raw, providers[0][0]


def hosted_entries(
    server, *, derived_names=(), surface: str = "mcp-hosted"
) -> list[dict]:
    """Rows for every tool the aggregate serves."""
    derived = set(derived_names)
    index = _peer_index(server)
    rows = []
    for tool in list_tools(server):
        namespace, raw, owner = attribute(tool.name, index)
        if owner is None:
            owner = owner_of(tool_owner(tool))[0]
        rows.append(
            {
                "kind": "mcp",
                "surface": surface,
                "package": owner,
                "path": None,
                "name": tool.name,
                "namespace": namespace,
                "raw_name": raw,
                "owner_package": owner,
                "owner_kind": owner_of(tool_owner(tool))[1]
                if tool_owner(tool)
                else "leaf",
                "implemented_in": tool_owner(tool),
                "input": input_summary(getattr(tool, "parameters", None)),
                "python_api": None,
                "derived_from_operation": raw in derived or tool.name in derived,
                "violations": mcp_name_rules(
                    tool.name, namespace, raw in derived or tool.name in derived
                ),
            }
        )
    return rows


__all__ = ["attribute", "hosted_entries"]
