#!/usr/bin/env python3
"""Normalization rules every inventoried endpoint and MCP tool is checked against.

The rules restate the operation grammar of :mod:`scitex_sdk.app.api_ops`
(the contract every leaf already builds on) as checks over ANY route — a
legacy Django view as well as a declared operation — so the distance from
today's surface to the contract is measurable per entry.

Rule ids are stable (``API-N<nn>``); a row lists the ids it violates. When
the v1 contract design publishes its own ids, :data:`RULES` gains an
``alias`` per rule rather than renumbering.
"""

from __future__ import annotations

import re

from ..api_ops import API_PREFIX, CRUD_VERBS

#: id -> (short title, what is checked)
RULES: dict[str, tuple[str, str]] = {
    "API-N01": ("unversioned", "API path is not under /api/v1/<package>/"),
    "API-N02": (
        "non-plural-resource",
        "the resource segment after /api/v1/<package>/ is not a plural noun",
    ),
    "API-N03": (
        "verb-in-path",
        "a CRUD verb (list/create/get/update/delete/...) appears in the path, "
        "or an action verb is not the final segment",
    ),
    "API-N04": (
        "casing",
        "a literal path segment is not lowercase kebab-case",
    ),
    "API-N05": (
        "trailing-slash",
        "the API path ends with '/' (operations are slash-less)",
    ),
    "API-N06": (
        "no-bearer-key",
        "the endpoint does not accept a SciTeX API key / OAuth token as "
        "'Authorization: Bearer' (session- or JWT-only, or a custom header)",
    ),
    "API-N07": (
        "no-problem-json",
        "errors are not declared as RFC 9457 problem+json (not served by the "
        "contract, or a live error response was not application/problem+json)",
    ),
    "API-N08": (
        "no-rest-mcp-twin",
        "REST and MCP are not 1:1: a REST operation without its derived MCP "
        "tool, or an MCP tool not derived from a declared operation",
    ),
    "API-N09": (
        "double-prefixed-mcp",
        "MCP tool name repeats its namespace (e.g. clew_clew_add_claim)",
    ),
    "API-N10": (
        "mcp-name-grammar",
        "MCP tool name is not <package>_<resource>_<verb>",
    ),
    "API-N11": (
        "hub-hosts-leaf-logic",
        "a hub-owned view imports leaf-package logic (the leaf should declare "
        "the operation; the hub only mounts it)",
    ),
    "API-N12": (
        "csrf-exempt-session",
        "CSRF-exempt endpoint without a non-session credential",
    ),
    "API-N13": (
        "unauthenticated-write",
        "state-changing method reachable with no authentication at all",
    ),
}

#: Words that are CRUD verbs (never allowed anywhere in a contract path).
CRUD_WORDS = frozenset(CRUD_VERBS) | {"add", "remove", "edit", "new", "save", "set", "put"}
#: Action-like words: allowed only as the final segment (POST <resource>/<verb>).
ACTION_WORDS = frozenset(
    {
        "submit",
        "cancel",
        "run",
        "execute",
        "compile",
        "verify",
        "publish",
        "search",
        "calculate",
        "describe",
        "recommend",
        "refresh",
        "register",
        "sync",
        "start",
        "stop",
        "restart",
        "import",
        "export",
        "enrich",
        "approve",
        "reject",
        "login",
        "logout",
        "chat",
        "convert",
        "render",
        "preview",
        "validate",
        "send",
        "mint",
        "rotate",
        "revoke",
        "extract",
        "concatenate",
        "fetch",
        "read",
        "write",
        "upload",
        "download",
        "rename",
        "move",
        "copy",
        "mkdir",
        "check",
        "switch",
        "toggle",
    }
)
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_PARAM = re.compile(r"^(<[^>]+>|\{[^}]+\}|\(\?P<[^>]+>.*\)|\*.*)$")
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
#: Credential modes that satisfy API-N06.
BEARER_KEY_MODES = frozenset({"api-key", "oauth", "contract"})


def literal_segments(path: str) -> list[str]:
    """The literal (non-parameter) segments of a normalized ``/a/{b}/c`` path."""
    return [s for s in path.strip("/").split("/") if s and not _PARAM.match(s)]


def segments(path: str) -> list[str]:
    return [s for s in path.strip("/").split("/") if s]


def _words(segment: str) -> set[str]:
    return set(re.split(r"[-_.]", segment.lower()))


def path_rules(path: str) -> list[str]:
    """Grammar rules (N01-N05) for one API path (already normalized)."""
    found = []
    segs = segments(path)
    prefix = API_PREFIX.split("/")
    versioned = segs[: len(prefix)] == prefix and len(segs) > len(prefix) + 1
    if not versioned:
        found.append("API-N01")
    else:
        resource = segs[len(prefix) + 1]
        if _PARAM.match(resource) or not resource.endswith("s"):
            found.append("API-N02")
    lits = literal_segments(path)
    for i, seg in enumerate(segs):
        if _PARAM.match(seg):
            continue
        words = _words(seg)
        if words & CRUD_WORDS:
            found.append("API-N03")
            break
        if words & ACTION_WORDS and i != len(segs) - 1:
            found.append("API-N03")
            break
    if any(not _KEBAB.match(s) for s in lits if s not in (".well-known",)):
        found.append("API-N04")
    if path.endswith("/") and path != "/":
        found.append("API-N05")
    return found


def route_rules(entry: dict) -> list[str]:
    """Every rule a REST/websocket/ASGI entry violates (``entry`` = inventory row)."""
    found = path_rules(entry["path"])
    auth = set(entry.get("auth") or ())
    if not entry.get("contract") and not (auth & (BEARER_KEY_MODES | {"signature"})):
        if "none" not in auth or entry.get("custom_key_header"):
            found.append("API-N06")
    if not entry.get("contract") or (entry.get("live") or {}).get("error_problem_json") is False:
        found.append("API-N07")
    if not entry.get("mcp_twin"):
        found.append("API-N08")
    if entry.get("owner_kind") == "hub" and entry.get("delegates_to"):
        found.append("API-N11")
    # Auth-provider libraries (token/OAuth endpoints) take credentials in the
    # body by design; N12/N13 judge application endpoints only.
    third_party = entry.get("owner_kind") == "third-party"
    if entry.get("csrf_exempt") and not third_party and not (auth - {"session", "none"}):
        found.append("API-N12")
    methods = set(entry.get("methods") or ())
    if (methods & WRITE_METHODS or "ANY" in methods) and auth == {"none"} and not third_party:
        found.append("API-N13")
    return sorted(set(found))


def mcp_name_rules(name: str, namespace: str | None, derived: bool) -> list[str]:
    """Rules N08-N10 for one MCP tool name."""
    found = []
    parts = name.split("_")
    if not derived and len(parts) >= 2 and parts[0] == parts[1]:
        found.append("API-N09")
    if namespace:
        ns = namespace.replace("-", "_")
        rest = name[len(ns) + 1 :] if name.startswith(ns + "_") else ""
        if rest.split("_")[:1] == [ns] or rest.startswith(ns + "_"):
            found.append("API-N09")
    if not derived:
        found.append("API-N08")
        found.append("API-N10")
    return sorted(set(found))


def rule_table() -> list[dict]:
    return [
        {"id": rid, "title": title, "check": check}
        for rid, (title, check) in RULES.items()
    ]


__all__ = [
    "RULES",
    "mcp_name_rules",
    "path_rules",
    "route_rules",
    "rule_table",
]
