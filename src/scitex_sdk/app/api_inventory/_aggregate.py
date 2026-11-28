#!/usr/bin/env python3
"""ONE aggregation over per-package listings — used by every global front end.

* umbrella ``scitex api list``  -> :func:`aggregate` over installed packages
* ``scitex-sdk api inventory``  -> the same, plus a host's Django URLconf,
  its ASGI mounts, its hosted MCP server and an optional live probe
* hub ``GET /api/v1/operations`` / scitex-dev audit -> the same function

There is no separate registry: the inputs are the packages' own
``scitex.apis`` declarations and MCP servers, and the host's URLconf.
"""

from __future__ import annotations

import importlib.metadata
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone

from ..api_plugin import discover_api_plugins
from ._ownership import is_ecosystem
from ._package import PackageSpec, distribution_version, list_package
from ._rules import route_rules, rule_table

SCHEMA = "scitex.api-inventory/v1"


def discover_specs(*, with_mcp: bool = True) -> list[PackageSpec]:
    """Every installed package that declares operations (or, with
    ``with_mcp``, every installed ecosystem distribution, MCP server or not)."""
    names = {ref.distribution for ref in discover_api_plugins()}
    if with_mcp:
        for dist in importlib.metadata.distributions():
            name = (dist.metadata.get("Name") or "").lower()
            if name and is_ecosystem(name) and name not in ("scitex", "scitex-python"):
                names.add(name)
    return [PackageSpec(n) for n in sorted(names)]


def _entry_id(row: dict) -> str:
    target = row.get("path") or row.get("name")
    return f"{row['kind']}:{row.get('surface')}:{','.join(row.get('methods') or [])}:{target}"


def link_contract_rows(rows: list[dict], operations: list[dict]) -> None:
    """Give URLconf rows served by the contract their operation's facts."""
    by_path = {op["path"]: op for op in operations}
    for row in rows:
        if not row.get("contract") or row["kind"] == "operation":
            continue
        op = by_path.get(row["path"].rstrip("/"))
        if op:
            row.update(
                methods=op["methods"],
                mcp_twin=op.get("mcp_twin"),
                operation_id=op.get("operation_id"),
                owner_package=op["owner_package"],
                owner_kind="leaf" if op["owner_package"] != "scitex-sdk" else "sdk",
            )


def aggregate(
    specs: list[PackageSpec] | None = None,
    *,
    urlconf: bool = False,
    asgi_module: str | None = None,
    hosted_mcp: str | None = None,
    probe: dict | None = None,
    include_pages: bool = True,
) -> dict:
    """The inventory document (see :data:`SCHEMA`)."""
    specs = discover_specs() if specs is None else specs
    entries, errors, packages = [], [], {}
    for spec in specs:
        listing = list_package(spec)
        packages[spec.distribution] = {
            "version": listing.version,
            "operations": len(listing.operations),
            "mcp_tools": len(listing.mcp_tools),
        }
        entries += listing.entries()
        errors += [f"{spec.distribution}: {e}" for e in listing.errors]
    operations = [e for e in entries if e["kind"] == "operation"]
    derived = {op["mcp_twin"] for op in operations if op.get("mcp_twin")}
    sources = {"packages": sorted(packages)}
    if urlconf:
        from ._django import apply_rules, urlconf_entries

        owners = {op["plugin"]: (op["owner_package"], "leaf") for op in operations}
        rows = urlconf_entries(plugin_owners=owners)
        link_contract_rows(rows, operations)
        apply_rules(rows)
        entries += rows if include_pages else [r for r in rows if r["kind"] != "page"]
        sources["urlconf"] = True
    if asgi_module:
        from ._django import apply_rules, asgi_entries

        entries += apply_rules(asgi_entries(asgi_module))
        sources["asgi_module"] = asgi_module
    if hosted_mcp:
        from ._hosted import hosted_entries
        from ._package import _import_ref

        entries += hosted_entries(_import_ref(hosted_mcp), derived_names=derived)
        sources["hosted_mcp"] = hosted_mcp
    probe_meta = None
    if probe:
        from ._probe import probe_rows

        probe_meta = probe_rows(entries, **probe)
        for row in entries:
            if row.get("live") and row["kind"] in ("rest", "asgi"):
                reconcile_live_auth(row)
                row["violations"] = route_rules(row)
    for row in entries:
        row["id"] = _entry_id(row)
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "package": "scitex-sdk",
            "version": distribution_version("scitex-sdk"),
            "python": platform.python_version(),
        },
        "sources": sources,
        "packages": packages,
        "probe": probe_meta,
        "rules": rule_table(),
        "totals": totals(entries),
        "clusters": clusters(entries),
        "errors": errors,
        "entries": entries,
    }


#: Anonymous behaviours that prove the server gates the endpoint.
GATED_BEHAVIOURS = frozenset({"unauthorized", "forbidden", "login-redirect"})


def reconcile_live_auth(row: dict) -> None:
    """Correct a static ``none`` verdict when the live server refused anonymity.

    Code analysis cannot see every in-body check (a helper that returns 403);
    an anonymous GET that is refused is evidence the endpoint is gated.
    """
    behaviour = (row.get("live") or {}).get("behaviour")
    if "none" in (row.get("auth") or ()) and behaviour in GATED_BEHAVIOURS:
        row["auth"] = sorted((set(row["auth"]) - {"none"}) | {"gated-in-body"})
        row.setdefault("auth_evidence", []).append(f"live:anonymous GET -> {behaviour}")
    with_token = (row.get("live") or {}).get("with_token") or {}
    if with_token.get("behaviour") == "open" and behaviour in GATED_BEHAVIOURS:
        row["auth"] = sorted(set(row["auth"]) | {"probe-token"})
        row.setdefault("auth_evidence", []).append("live:probe bearer token -> open")


def programmatic(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e["kind"] != "page"]


def totals(entries: list[dict]) -> dict:
    api = programmatic(entries)
    auth = Counter(
        mode for e in api if e["kind"] != "mcp" for mode in e.get("auth") or ["n/a"]
    )
    rules = Counter(r for e in api for r in e.get("violations") or ())
    live = Counter((e.get("live") or {}).get("behaviour") for e in api if e.get("live"))
    return {
        "entries": len(entries),
        "pages": len(entries) - len(api),
        "programmatic": len(api),
        "by_kind": dict(Counter(e["kind"] for e in api)),
        "by_surface": dict(Counter(e.get("surface") for e in api)),
        "by_owner_kind": dict(Counter(e.get("owner_kind") for e in api)),
        "by_owner_package": dict(
            Counter(e.get("owner_package") for e in api).most_common()
        ),
        "by_auth_mode": dict(auth.most_common()),
        "versioned": sum(1 for e in api if e["kind"] != "mcp" and e.get("versioned")),
        "unversioned": sum(
            1 for e in api if e["kind"] != "mcp" and not e.get("versioned")
        ),
        "by_rule": dict(sorted(rules.items())),
        "conformant": sum(1 for e in api if not e.get("violations")),
        "live": dict(live.most_common()),
    }


def cluster_key(row: dict) -> tuple:
    if row["kind"] == "mcp":
        return row.get(
            "owner_package"
        ), f"mcp:{row.get('surface')}:{row.get('namespace') or '-'}"
    segs = [
        s for s in (row.get("path") or "").strip("/").split("/") if s and "{" not in s
    ]
    return row.get("owner_package"), "/" + "/".join(segs[:2])


def clusters(entries: list[dict], limit: int = 25) -> list[dict]:
    """Violating programmatic rows grouped by (owner, path prefix / namespace)."""
    groups: dict = defaultdict(list)
    for row in programmatic(entries):
        if row.get("violations"):
            groups[cluster_key(row)].append(row)
    out = []
    for (owner, prefix), rows in groups.items():
        rules = Counter(r for row in rows for r in row["violations"])
        out.append(
            {
                "owner_package": owner,
                "prefix": prefix,
                "count": len(rows),
                "rules": dict(rules.most_common()),
                "examples": [row.get("path") or row.get("name") for row in rows[:4]],
            }
        )
    out.sort(key=lambda c: (-c["count"] * len(c["rules"]), c["prefix"]))
    return out[:limit]


__all__ = ["SCHEMA", "aggregate", "clusters", "discover_specs", "totals"]
