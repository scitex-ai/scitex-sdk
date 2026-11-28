#!/usr/bin/env python3
"""Resolve a host's Django URLconf (and ASGI mounts) into inventory rows.

Runs inside the host's own interpreter after ``django.setup()``: every URL
pattern — includes, DRF routers, plugin mounts, the generic ``/api/v1``
contract mount — is reached through ``get_resolver()``, so the inventory is
what Django would actually route, not what a grep finds. Per-view analysis
lives in :mod:`._view_auth` and :mod:`._ownership`.
"""

from __future__ import annotations

import ast
import importlib
import re

from ..api_ops import API_PREFIX
from ._ownership import HUB_TOP_LEVEL, delegates_to, owner_of
from ._rules import route_rules
from ._view_auth import auth_profile, http_methods, is_drf, source, view_target

_API_HEADS = ("api", "v1", ".well-known", "oauth", "mcp")


def normalize_path(raw: str) -> str:
    """``^api/(?P<pk>\\d+)/$`` / ``api/<int:pk>/`` -> ``/api/{pk}/``."""
    path = raw
    for token in ("^", "$", "\\Z", "\\A"):
        path = path.replace(token, "")
    path = re.sub(
        r"\(\?P<([A-Za-z_][A-Za-z0-9_]*)>(?:[^()]|\([^()]*\))*\)", r"{\1}", path
    )
    path = re.sub(r"\((?!\?P)(?:[^()]|\([^()]*\))*\)\??", "{arg}", path)
    path = re.sub(r"<(?:[a-z_]+:)?([A-Za-z_][A-Za-z0-9_]*)>", r"{\1}", path)
    path = path.replace("\\.", ".").replace("\\-", "-").replace("\\", "")
    path = re.sub(r"\.\*|\.\+|\[\^/\]\+", "{rest}", path)
    return "/" + path.lstrip("/")


def iter_patterns(patterns, prefix: str = "", urlconf: str | None = None):
    """Yield ``(raw_path, URLPattern, including_urlconf)`` depth-first."""
    for p in patterns:
        if hasattr(p, "url_patterns"):
            module = getattr(p, "urlconf_name", None)
            name = (
                module if isinstance(module, str) else getattr(module, "__name__", None)
            )
            yield from iter_patterns(
                p.url_patterns, prefix + str(p.pattern), name or urlconf
            )
        else:
            yield prefix + str(p.pattern), p, urlconf


def is_api_path(path: str, drf: bool) -> bool:
    """Programmatic (API) route vs HTML page, by path shape (and DRF)."""
    segs = [s for s in path.strip("/").split("/") if s]
    if drf:
        return True
    if not segs:
        return False
    if segs[0] in _API_HEADS:
        return True
    if any(s == "api" or s.startswith("api-") or s.endswith("-api") for s in segs):
        return True
    return any("webhook" in s for s in segs)


def contract_plugin_of(path: str) -> str | None:
    prefix = "/" + API_PREFIX + "/"
    if path.startswith(prefix):
        segment = path[len(prefix) :].split("/")[0]
        return segment if segment and not segment.startswith("{") else None
    return None


def _middleware_bearer() -> tuple:
    from django.conf import settings

    middleware = tuple(getattr(settings, "MIDDLEWARE", ()))
    return ("jwt",) if any("jwt" in m.lower() for m in middleware) else ()


def _contract_profile() -> dict:
    return {
        "auth": ["contract"],
        "permission": "scope",
        "csrf_exempt": False,
        "auth_evidence": ["scitex_sdk.app.api_serve"],
        "custom_key_header": False,
    }


def urlconf_entries(
    resolver=None, *, plugin_owners: dict | None = None, host_packages=HUB_TOP_LEVEL
) -> list[dict]:
    """Every URL pattern of the configured Django project, as inventory rows.

    ``plugin_owners`` maps a contract plugin id to its ``(distribution,
    kind)`` so routes served by the generic ``/api/v1`` mount are owned by
    the leaf that declared them, not by the SDK adapter that serves them.
    """
    from django.urls import get_resolver

    resolver = resolver or get_resolver()
    bearer = _middleware_bearer()
    plugin_owners = plugin_owners or {}
    rows = []
    for raw, pattern, urlconf in iter_patterns(resolver.url_patterns):
        cb = pattern.callback
        kind, target = view_target(cb)
        module = getattr(target, "__module__", None) or getattr(cb, "__module__", None)
        qual = getattr(target, "__qualname__", repr(target))
        path = normalize_path(raw)
        owner, owner_kind = owner_of(module, host_packages)
        contract = bool(module and module.startswith("scitex_sdk.app.api_serve"))
        plugin = contract_plugin_of(path) if contract else None
        if contract and plugin:
            owner, owner_kind = plugin_owners.get(plugin, (plugin, "leaf"))
        drf = is_drf(cb)
        profile = (
            _contract_profile()
            if contract
            else auth_profile(cb, middleware_bearer=bearer)
        )
        app_module = module
        if module and module.startswith("apps."):
            app_module = ".".join(module.split(".")[:3])
        rows.append(
            {
                "kind": "rest" if contract or is_api_path(path, drf) else "page",
                "surface": "hub-urlconf",
                "path": path,
                "raw_pattern": raw,
                "name": pattern.name,
                "view": f"{module}.{qual}" if module else qual,
                "view_kind": "drf" if drf else kind,
                "methods": ["ANY"] if contract else http_methods(cb),
                "urlconf": urlconf,
                "owner_package": owner,
                "owner_kind": owner_kind,
                "app_module": app_module,
                "delegates_to": delegates_to(cb) if owner_kind == "hub" else [],
                "contract": contract,
                "plugin": plugin,
                "versioned": path.startswith("/" + API_PREFIX + "/"),
                "mcp_twin": None,
                **profile,
            }
        )
    return rows


def _find_url_router(app, depth: int = 0):
    if app is None or depth > 8:
        return None
    if hasattr(app, "routes"):
        return app
    for attr in ("inner", "application", "app"):
        found = _find_url_router(getattr(app, attr, None), depth + 1)
        if found is not None:
            return found
    return None


def _asgi_row(**fields) -> dict:
    base = {
        "surface": "hub-asgi",
        "name": None,
        "csrf_exempt": False,
        "contract": False,
        "delegates_to": [],
        "mcp_twin": None,
        "custom_key_header": False,
    }
    base.update(fields)
    base["versioned"] = base["path"].startswith("/" + API_PREFIX + "/")
    return base


def _websocket_rows(app) -> list[dict]:
    mapping = getattr(app, "application_mapping", {}) or {}
    router = _find_url_router(mapping.get("websocket"))
    rows = []
    for raw, pattern, _ in iter_patterns(getattr(router, "routes", ())):
        cb = getattr(pattern, "callback", None)
        target = getattr(cb, "consumer_class", None) or cb
        mod = getattr(target, "__module__", None)
        owner, owner_kind = owner_of(mod)
        rows.append(
            _asgi_row(
                kind="websocket",
                path=normalize_path(raw),
                raw_pattern=raw,
                name=getattr(pattern, "name", None),
                view=f"{mod}.{getattr(target, '__qualname__', target)}",
                methods=["WS"],
                owner_package=owner,
                owner_kind=owner_kind,
                auth=["session"],
                permission="consumer",
                auth_evidence=["channels AuthMiddlewareStack"],
            )
        )
    return rows


def _path_literal(node) -> str | None:
    if isinstance(node, ast.Compare) and isinstance(node.comparators[0], ast.Constant):
        return node.comparators[0].value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "startswith"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ):
        return node.args[0].value
    return None


def asgi_entries(module_name: str) -> list[dict]:
    """Websocket routes and HTTP path mounts (e.g. ``/mcp``) of an ASGI module.

    HTTP mounts are the path literals an ASGI router function compares
    ``scope["path"]`` against; the authorization calls made in that function
    are recorded as evidence (the live probe shows the behaviour).
    """
    module = importlib.import_module(module_name)
    rows = _websocket_rows(getattr(module, "application", None))
    src = source(module)
    tree = ast.parse(src) if src else ast.Module(body=[], type_ignores=[])
    funcs = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
    ]
    for func in funcs:
        for node in ast.walk(func):
            lit = _path_literal(node)
            if not (isinstance(lit, str) and lit.startswith("/") and lit.rstrip("/")):
                continue
            path = lit.rstrip("/")
            if any(r["path"] == path for r in rows):
                continue
            calls = sorted(
                {
                    ast.unparse(c.func).split(".")[-1]
                    for c in ast.walk(func)
                    if isinstance(c, ast.Call) and "auth" in ast.unparse(c.func).lower()
                }
            )
            rows.append(
                _asgi_row(
                    kind="asgi",
                    path=path,
                    raw_pattern=lit,
                    view=f"{module_name}.{func.name}",
                    methods=["ANY"],
                    owner_package="scitex-hub",
                    owner_kind="hub",
                    auth=["custom"] if calls else ["none"],
                    permission=",".join(calls) or "public",
                    auth_evidence=[f"call:{c}" for c in calls],
                    csrf_exempt=True,
                )
            )
    return rows


def apply_rules(rows: list[dict]) -> list[dict]:
    """Attach ``violations`` to every programmatic row (pages get none)."""
    for row in rows:
        row["violations"] = route_rules(row) if row["kind"] != "page" else []
    return rows


__all__ = [
    "apply_rules",
    "asgi_entries",
    "contract_plugin_of",
    "is_api_path",
    "iter_patterns",
    "normalize_path",
    "urlconf_entries",
]
