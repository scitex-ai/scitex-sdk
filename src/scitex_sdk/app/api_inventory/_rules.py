#!/usr/bin/env python3
"""Contract rules every inventoried endpoint and MCP tool is checked against.

Rule ids are the stable ids of the API contract v1 rule registry
(``docs/design/api-contract-v1/01-rules.md``): the same id appears in the
declaration-time exception, the contract test, the scitex-dev audit and
here. The inventory checks the subset that can be judged from a route, a
tool name and a live response; ``API-X*`` are inventory-only findings the
registry does not (yet) carry.

A legacy Django view is judged by the same grammar as a declared
operation, so the distance from today's surface to the contract is
measurable per entry.
"""

from __future__ import annotations

import re

from ..api_ops import API_PREFIX, CRUD_VERBS

CONTRACT_DOC = "docs/design/api-contract-v1/01-rules.md"

#: id -> (short title, what the inventory checks)
RULES: dict[str, tuple[str, str]] = {
    "API-D001": (
        "not-generated",
        "public API route not generated from an ApiOperation of an admitted plugin",
    ),
    "API-D005": (
        "dynamic-dispatcher",
        "catch-all or generic dispatcher (<path:...>, {module}/{function}) in the route",
    ),
    "API-R001": (
        "off-url-grammar",
        "path is not /api/v1/<package>/<resource>[/{id}][/<action>]",
    ),
    "API-R002": ("casing", "a literal path segment is not lowercase kebab-case"),
    "API-R003": ("non-plural-resource", "the resource segment is not a plural noun"),
    "API-R004": ("trailing-slash", "the API path ends with '/'"),
    "API-V002": (
        "verb-in-path",
        "a CRUD verb in the path (the method carries it), or an action verb that is not the final segment",
    ),
    "API-A001": (
        "no-bearer",
        "programs cannot use 'Authorization: Bearer <token>' (session/JWT-only, custom key "
        "header, or a CSRF-exempt session endpoint)",
    ),
    "API-A004": (
        "anonymous-write",
        "a declared write method (POST/PUT/PATCH/DELETE) with no authentication found in code "
        "and none observed live",
    ),
    "API-E001": (
        "no-problem-json",
        "errors are not RFC 9457 problem+json (not served by the contract, or a live error "
        "response was another content type)",
    ),
    "API-E003": (
        "html-or-login-on-api",
        "an API path answered HTML or redirected to a login page",
    ),
    "API-T001": (
        "tool-name-grammar",
        "MCP tool name is not <package>_<resource>_<verb>",
    ),
    "API-T002": (
        "no-rest-mcp-twin",
        "REST and MCP are not 1:1: an operation without its derived tool, or a tool not "
        "derived from an operation",
    ),
    "API-T003": (
        "re-namespaced-tool",
        "MCP tool name repeats its namespace (clew_clew_add_claim)",
    ),
    "API-X001": (
        "hub-hosts-leaf-logic",
        "inventory-only: a hub-owned view calls leaf-package logic (the leaf should declare "
        "the operation; the hub only docks it)",
    ),
}

#: CRUD verbs, which the HTTP method carries: never a path segment.
CRUD_WORDS = frozenset(CRUD_VERBS) | {
    "add",
    "remove",
    "edit",
    "new",
    "save",
    "set",
    "put",
}
#: Action-like words: allowed only as the final segment (POST <resource>/<verb>).
ACTION_WORDS = frozenset(
    ["submit", "cancel", "run", "execute", "compile", "verify", "publish", "search", "calculate", "describe", "recommend", "refresh", "register", "sync", "start", "stop", "restart", "import", "export", "enrich", "approve", "reject", "login", "logout", "chat", "convert", "render", "preview", "validate", "send", "mint", "rotate", "revoke", "extract", "concatenate", "fetch", "read", "write", "upload", "download", "rename", "move", "copy", "mkdir", "check", "switch", "toggle"]
)
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_PARAM = re.compile(r"^(<[^>]+>|\{[^}]+\}|\(\?P<[^>]+>.*\)|\*.*)$")
_DISPATCH_PARAMS = {
    "{path}",
    "{endpoint}",
    "{rest}",
    "{module}",
    "{function}",
    "{subpath}",
}
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
#: Credential modes that satisfy API-A001 (a Bearer token programs can mint).
BEARER_MODES = frozenset({"api-key", "oauth", "contract"})


def segments(path: str) -> list[str]:
    return [s for s in path.strip("/").split("/") if s]


def literal_segments(path: str) -> list[str]:
    """The literal (non-parameter) segments of a normalized ``/a/{b}/c`` path."""
    return [s for s in segments(path) if not _PARAM.match(s)]


def _words(segment: str) -> set[str]:
    return set(re.split(r"[-_.]", segment.lower()))


def path_rules(path: str, raw_pattern: str = "") -> list[str]:
    """URL-grammar rules (D005, R001-R004, V002) for one normalized API path."""
    found = []
    segs = segments(path)
    prefix = API_PREFIX.split("/")
    if not (segs[: len(prefix)] == prefix and len(segs) > len(prefix) + 1):
        found.append("API-R001")
    else:
        resource = segs[len(prefix) + 1]
        if _PARAM.match(resource) or not resource.endswith("s"):
            found.append("API-R003")
    for i, seg in enumerate(segs):
        if _PARAM.match(seg):
            continue
        words = _words(seg)
        if words & CRUD_WORDS or (words & ACTION_WORDS and i != len(segs) - 1):
            found.append("API-V002")
            break
    if any(not _KEBAB.match(s) for s in literal_segments(path) if s != ".well-known"):
        found.append("API-R002")
    if path.endswith("/") and path != "/":
        found.append("API-R004")
    if "<path:" in raw_pattern or set(segs) & _DISPATCH_PARAMS:
        found.append("API-D005")
    return found


def route_rules(entry: dict) -> list[str]:
    """Every rule a REST/websocket/ASGI entry (an inventory row) violates."""
    found = path_rules(entry["path"], entry.get("raw_pattern") or "")
    auth = set(entry.get("auth") or ())
    contract = bool(entry.get("contract"))
    third_party = entry.get("owner_kind") == "third-party"
    live = entry.get("live") or {}
    if not contract:
        found += ["API-D001", "API-E001"]
        if not auth & (BEARER_MODES | {"signature"}):
            if "none" not in auth or entry.get("custom_key_header"):
                found.append("API-A001")
    elif live.get("error_problem_json") is False:
        found.append("API-E001")
    # A CSRF-exempt endpoint whose only credential is the session cookie.
    if (
        entry.get("csrf_exempt")
        and not third_party
        and not (auth - {"session", "none", "gated-in-body"})
    ):
        found.append("API-A001")
    if (
        live.get("behaviour") == "login-redirect"
        or live.get("content_type") == "text/html"
    ):
        found.append("API-E003")
    if not entry.get("mcp_twin"):
        found.append("API-T002")
    if entry.get("owner_kind") == "hub" and entry.get("delegates_to"):
        found.append("API-X001")
    methods = set(entry.get("methods") or ())
    # Only an explicitly declared write method counts: an unrestricted (ANY)
    # view is usually a GET endpoint, and the live probe judges those.
    if methods & WRITE_METHODS and auth == {"none"} and not third_party:
        found.append("API-A004")
    return sorted(set(found))


def mcp_name_rules(name: str, namespace: str | None, derived: bool) -> list[str]:
    """Rules T001-T003 for one MCP tool name."""
    found = []
    parts = name.split("_")
    if not derived and len(parts) >= 2 and parts[0] == parts[1]:
        found.append("API-T003")
    if namespace:
        ns = namespace.replace("-", "_")
        rest = name[len(ns) + 1 :] if name.startswith(ns + "_") else ""
        if rest.startswith(ns + "_"):
            found.append("API-T003")
    if not derived:
        found += ["API-T001", "API-T002"]
    return sorted(set(found))


def rule_table() -> list[dict]:
    return [
        {
            "id": rid,
            "title": title,
            "check": check,
            "source": CONTRACT_DOC if not rid.startswith("API-X") else "inventory",
        }
        for rid, (title, check) in RULES.items()
    ]


__all__ = [
    "CONTRACT_DOC",
    "RULES",
    "mcp_name_rules",
    "path_rules",
    "route_rules",
    "rule_table",
]
