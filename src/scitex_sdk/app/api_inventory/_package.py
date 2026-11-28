#!/usr/bin/env python3
"""One package's API surface: its declared operations and its MCP tools.

This is what ``scitex-<pkg> api list`` prints and what every aggregate
(umbrella ``scitex api list``, ``scitex-sdk api inventory``, the hub) is
composed of. Nothing here needs Django or a running server.

* **Operations** come from the package's ``scitex.apis`` entry points, read
  back through :func:`scitex_sdk.app.api_ops.operation_of` — the same code
  path the host's admission and the contract tests use, so a route the host
  would refuse is reported here as an ``off-grammar`` finding.
* **MCP tools** come from the package's FastMCP server (``module:attr``,
  stated by the package, or found at the ecosystem's canonical locations).
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.metadata
import inspect
from dataclasses import dataclass, field

from ..api_ops import API_PREFIX, operation_of
from ..api_plugin import ApiPluginContractError, discover_api_plugins
from ._rules import mcp_name_rules, path_rules

#: Where a package's FastMCP instance conventionally lives (the umbrella
#: ``scitex mcp`` resolves peers through the same list).
MCP_MODULE_CANDIDATES = (
    "_mcp_server",
    "mcp_server",
    "_mcp.server",
    "mcp.server",
    "_server",
    "_mcp._server",
)
MCP_ATTR_CANDIDATES = ("mcp", "server", "app")


@dataclass
class PackageSpec:
    """Which package to list, and where its MCP server is (optional)."""

    distribution: str
    import_name: str | None = None
    mcp_server: str | None = None  # "module:attr"; None = conventional lookup
    namespace: str | None = None  # MCP namespace when mounted by an aggregator

    def __post_init__(self) -> None:
        if self.import_name is None:
            self.import_name = self.distribution.replace("-", "_")


@dataclass
class PackageListing:
    spec: PackageSpec
    version: str | None
    operations: list = field(default_factory=list)
    mcp_tools: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def entries(self) -> list[dict]:
        return self.operations + self.mcp_tools


def distribution_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _import_ref(ref: str):
    module, _, attr = ref.partition(":")
    obj = importlib.import_module(module)
    for part in attr.split(".") if attr else ():
        obj = getattr(obj, part)
    return obj


def find_mcp_server(spec: PackageSpec):
    """The package's FastMCP instance, or None when it ships none."""
    if spec.mcp_server:
        return _import_ref(spec.mcp_server)
    try:
        from fastmcp import FastMCP
    except ImportError:
        return None
    for sub in MCP_MODULE_CANDIDATES:
        try:
            module = importlib.import_module(f"{spec.import_name}.{sub}")
        except Exception:  # an absent or broken candidate is simply not it
            continue
        for attr in MCP_ATTR_CANDIDATES:
            obj = getattr(module, attr, None)
            if isinstance(obj, FastMCP):
                return obj
    return None


def list_tools(server) -> list:
    """Every tool of a FastMCP server (``list_tools`` is async in fastmcp)."""
    result = server.list_tools()
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return list(result.values()) if isinstance(result, dict) else list(result)


def input_summary(schema: dict | None) -> str:
    """``a*, b, c`` — the tool's parameters, required ones starred."""
    schema = schema or {}
    required = set(schema.get("required") or ())
    names = list((schema.get("properties") or {}).keys())
    return ", ".join(n + ("*" if n in required else "") for n in names)


def tool_owner(tool) -> str | None:
    """Top-level module that implements a tool, when fastmcp exposes it."""
    fn = getattr(tool, "fn", None)
    module = getattr(fn, "__module__", None)
    return module.split(".")[0] if module else None


def python_api_for(
    import_name: str, tool_name: str, namespace: str | None
) -> str | None:
    """A public callable of the package with the tool's base name, if any.

    Matching is by name: ``<pkg>_<name>`` -> ``<pkg>.<name>``, then
    ``<pkg>.<tool_name>``. A tool whose logic has no public Python twin
    returns None (the finding the inventory reports).
    """
    try:
        package = importlib.import_module(import_name)
    except Exception:
        return None
    candidates = []
    for prefix in filter(None, (namespace, import_name.removeprefix("scitex_"))):
        prefix = prefix.replace("-", "_") + "_"
        if tool_name.startswith(prefix):
            candidates.append(tool_name[len(prefix) :])
    candidates.append(tool_name)
    for name in candidates:
        obj = getattr(package, name, None)
        if callable(obj) and not name.startswith("_"):
            return f"{import_name}.{name}"
    return None


def operation_entries(distribution: str, refs=None) -> tuple[list[dict], list[str]]:
    """Rows for every declared operation of ``distribution`` (contract)."""
    rows, errors = [], []
    for ref in refs if refs is not None else discover_api_plugins():
        if ref.distribution != distribution:
            continue
        try:
            plugin = _import_ref(ref.target)
        except Exception as exc:
            errors.append(f"{ref.name}: cannot load {ref.target}: {exc}")
            continue
        for route in plugin.routes:
            path = f"/{API_PREFIX}/{plugin.id}/{route.path}"
            row = {
                "kind": "operation",
                "surface": "contract",
                "package": distribution,
                "plugin": plugin.id,
                "path": path,
                "methods": list(route.methods),
                "name": None,
                "view": route.handler,
                "owner_package": distribution,
                "owner_kind": "leaf",
                "auth": ["none"] if route.auth.public else ["contract"],
                "permission": ",".join(route.auth.scopes) or route.auth.project_scope,
                "contract": True,
                "versioned": True,
                "csrf_exempt": False,
            }
            try:
                op = operation_of(plugin, route)
            except ApiPluginContractError as exc:
                row.update(
                    operation_id=None,
                    mcp_twin=None,
                    off_grammar=str(exc),
                    violations=sorted(set(path_rules(path)) | {"API-N08"}),
                )
            else:
                row.update(
                    operation_id=op.operation_id,
                    mcp_twin=op.mcp_name,
                    scope=op.scope,
                    off_grammar=None,
                    violations=path_rules(path),
                )
            rows.append(row)
    return rows, errors


def mcp_entries(
    spec: PackageSpec, server, *, surface: str, derived_names=()
) -> list[dict]:
    """Rows for every tool of ``server`` (owned by ``spec``)."""
    derived = set(derived_names)
    rows = []
    for tool in list_tools(server):
        name = tool.name
        namespace = spec.namespace or spec.import_name.removeprefix("scitex_")
        rows.append(
            {
                "kind": "mcp",
                "surface": surface,
                "package": spec.distribution,
                "path": None,
                "name": name,
                "namespace": namespace,
                "owner_package": spec.distribution,
                "owner_kind": "leaf",
                "implemented_in": tool_owner(tool),
                "input": input_summary(getattr(tool, "parameters", None)),
                "python_api": python_api_for(spec.import_name, name, namespace),
                "derived_from_operation": name in derived,
                "violations": mcp_name_rules(name, namespace, name in derived),
            }
        )
    return rows


def list_package(spec: PackageSpec | str, refs=None) -> PackageListing:
    """The full API listing of one package (operations + MCP tools)."""
    if isinstance(spec, str):
        spec = PackageSpec(spec)
    listing = PackageListing(spec, distribution_version(spec.distribution))
    listing.operations, listing.errors = operation_entries(spec.distribution, refs)
    derived = [r["mcp_twin"] for r in listing.operations if r.get("mcp_twin")]
    try:
        server = find_mcp_server(spec)
    except Exception as exc:
        listing.errors.append(f"cannot load MCP server: {exc}")
        server = None
    if server is not None:
        listing.mcp_tools = mcp_entries(
            spec, server, surface="mcp-leaf", derived_names=derived
        )
    names = {r["name"] for r in listing.mcp_tools}
    for row in listing.operations:
        twin = row.get("mcp_twin")
        row["mcp_twin_served"] = bool(twin) and (server is None or twin in names)
        if twin and server is not None and twin not in names:
            row["violations"] = sorted(set(row["violations"]) | {"API-N08"})
    return listing


__all__ = [
    "MCP_ATTR_CANDIDATES",
    "MCP_MODULE_CANDIDATES",
    "PackageListing",
    "PackageSpec",
    "find_mcp_server",
    "input_summary",
    "list_package",
    "list_tools",
    "mcp_entries",
    "operation_entries",
]
