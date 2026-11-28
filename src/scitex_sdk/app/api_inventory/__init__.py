#!/usr/bin/env python3
"""Deterministic inventory of SciTeX API endpoints and MCP tools.

Per package (``scitex-<pkg> api list``, via :func:`api_click_group`):
declared ``scitex.apis`` operations + the package's MCP tools + rule findings.
Globally (umbrella ``scitex api list``, ``scitex-sdk api inventory``, a hub,
a CI audit): :func:`aggregate` composes those per-package listings with a
host's Django URLconf, ASGI mounts, hosted MCP server and a live GET probe.
Every row carries the normalization rules (:data:`RULES`) it violates.
"""

from ._aggregate import SCHEMA, aggregate, clusters, discover_specs, totals
from ._cli import api_click_group, inventory_command, sdk_api_group
from ._package import PackageListing, PackageSpec, list_package
from ._render import RENDERERS, to_csv, to_json, to_markdown
from ._rules import RULES, mcp_name_rules, path_rules, route_rules, rule_table

__all__ = [
    "RENDERERS",
    "RULES",
    "SCHEMA",
    "PackageListing",
    "PackageSpec",
    "aggregate",
    "api_click_group",
    "clusters",
    "discover_specs",
    "inventory_command",
    "list_package",
    "mcp_name_rules",
    "path_rules",
    "route_rules",
    "rule_table",
    "sdk_api_group",
    "to_csv",
    "to_json",
    "to_markdown",
    "totals",
]
