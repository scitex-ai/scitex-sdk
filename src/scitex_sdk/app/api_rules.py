#!/usr/bin/env python3
"""Stable rule ids of the SciTeX API contract v1, and the checks that need them.

Every declaration-time refusal of the operation layer names the rule it
enforces, so a leaf author, the contract test (:mod:`scitex_sdk.testing.api_contract`),
the Dev audit (``PS-SDK-WEB``) and a host's refusal log all print the same line::

    ApiContractViolation: [API-R003] clew.data.list: resource 'data' must be a plural noun

The registry lives in ``docs/design/api-contract-v1/01-rules.md``; :data:`RULES`
names the ids this SDK enforces in code. :class:`ApiContractViolation` is an
:class:`~.api_plugin.ApiPluginContractError`, so existing ``except`` clauses keep
working.
"""

from __future__ import annotations

import re

from .api_plugin import ApiPluginContractError

RULES_DOC = "docs/design/api-contract-v1/01-rules.md"

#: Rule ids enforced in code, with where they are enforced (D = declaration,
#: C = contract test, R = runtime host).
RULES = {
    "API-D001": ("C", "every public route is generated from an ApiOperation"),
    "API-D003": ("D", "declared contract major is supported"),
    "API-A004": ("D", "only a non-project read may be public"),
    "API-D005": ("D", "no catch-all or dynamic dispatcher route"),
    "API-D006": ("D", "handler is a module:function string"),
    "API-R001": ("D", "URL grammar /api/v1/<package>/<resource>[/{id}][/<action>]"),
    "API-R002": ("D", "lowercase kebab-case package, resource and action names"),
    "API-R003": ("D", "resource is a plural noun"),
    "API-R004": ("R", "no trailing slash"),
    "API-R006": ("D", "reserved top-level names are not packages"),
    "API-V001": ("D", "CRUD verbs fix method, item-ness and status"),
    "API-V002": ("D", "actions state item=True or item=False"),
    "API-V004": ("D", "read_only applies to actions only"),
    "API-F001": ("D", "snake_case fields, parameters and enum values"),
    "API-E002": ("D", "leaf error codes are <package>.<snake>"),
    "API-G001": ("D", "only list is paginated; 1 <= default <= max <= 200"),
    "API-J001": ("D", "an async operation's Job schema carries id and state"),
    "API-H002": ("D", "rate class from the closed set"),
    "API-K001": ("D", "compute cost from the closed set"),
    "API-T001": ("D", "MCP tool name derived and unique"),
    "API-T002": ("C", "MCP tools and operations map 1:1"),
    "API-O001": ("C", "OpenAPI generated and operationIds derived"),
    "API-O002": ("C", "the OpenAPI document validates"),
    "API-A002": ("C", "a missing or invalid bearer is a 401 problem"),
    "API-A003": ("C", "scope derived and enforced (403 without it)"),
    "API-E001": ("C", "errors are application/problem+json"),
    "API-I001": ("C", "writes require Idempotency-Key"),
    "API-V005": ("C", "wrong method is a 405 problem"),
    "API-C001": ("C", "additive-only changes within v1"),
}

#: Contract majors this SDK can build and serve.
CONTRACT_MAJOR = "1"
SUPPORTED_CONTRACTS = frozenset({CONTRACT_MAJOR})
#: Top-level ``/api/v1/`` names that are not packages (API-R006).
RESERVED_PACKAGES = frozenset({"operations", "openapi", "mcp", "health"})
COMPUTE_COSTS = ("light", "standard", "heavy")
RATE_CLASSES = ("anonymous", "standard", "search", "bulk", "interactive")
MAX_PAGE_LIMIT = 200
JOB_REQUIRED_FIELDS = ("id", "state")

SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_ENUM_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
_HANDLER_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:"
    r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


class ApiContractViolation(ApiPluginContractError):
    """A declaration violates rule ``rule`` of the API contract."""

    def __init__(self, rule: str, message: str, operation_id: str | None = None):
        self.rule = rule
        self.operation_id = operation_id
        self.detail = message
        where = f"{operation_id}: " if operation_id else ""
        super().__init__(f"[{rule}] {where}{message}")


def violation(rule: str, message: str, operation_id: str | None = None):
    """The exception for ``rule`` (raise it)."""
    if rule not in RULES:  # pragma: no cover - a typo in the SDK itself
        raise KeyError(f"unknown API rule id {rule!r}")
    return ApiContractViolation(rule, message, operation_id)


def _field_violations(fields, where: str):
    for item in fields:
        is_sort = item.name == "sort"
        if not SNAKE_RE.match(item.name):
            yield "API-F001", f"{where} field {item.name!r} must be snake_case"
        for value in item.enum or ():
            text = str(value)
            if is_sort and text.startswith("-"):
                text = text[1:]
            if not _ENUM_RE.match(text):
                yield (
                    "API-F001",
                    (
                        f"{where} field {item.name!r} enum value {value!r} must be "
                        "lowercase snake_case"
                    ),
                )


def operation_violations(op) -> list:
    """Every contract violation of one operation, as ``(rule, message)``.

    Called by ``ApiOperation.__post_init__`` (which raises the first) and by the
    contract test (which reports all of them).
    """
    out = []
    if not _HANDLER_RE.match(op.handler or ""):
        out.append(("API-D006", f"handler {op.handler!r} must be 'module:function'"))
    if op.package in RESERVED_PACKAGES:
        out.append(("API-R006", f"package {op.package!r} is a reserved /api/v1 name"))
    if op.compute_cost not in COMPUTE_COSTS:
        out.append(
            (
                "API-K001",
                f"compute_cost {op.compute_cost!r} must be one of {COMPUTE_COSTS}",
            )
        )
    if op.rate_class not in RATE_CLASSES:
        out.append(
            ("API-H002", f"rate_class {op.rate_class!r} must be one of {RATE_CLASSES}")
        )
    if op.paginated and not 1 <= op.default_limit <= op.max_limit <= MAX_PAGE_LIMIT:
        out.append(
            (
                "API-G001",
                f"page limits must satisfy 1 <= default ({op.default_limit}) <= "
                f"max ({op.max_limit}) <= {MAX_PAGE_LIMIT}",
            )
        )
    out.extend(_field_violations(op.params, "request"))
    if op.response is not None:
        out.extend(_field_violations(op.response.fields, "response"))
        if op.is_async:
            names = {f.name for f in op.response.fields}
            missing = [n for n in JOB_REQUIRED_FIELDS if n not in names]
            if missing:
                out.append(("API-J001", f"the Job schema lacks field(s) {missing}"))
    prefix = f"{op.package}."
    for error in op.errors:
        tail = error.code[len(prefix) :] if error.code.startswith(prefix) else ""
        if not SNAKE_RE.match(tail):
            out.append(
                (
                    "API-E002",
                    f"error code {error.code!r} must be '{prefix}<snake_case>'",
                )
            )
    return out


__all__ = [
    "COMPUTE_COSTS",
    "CONTRACT_MAJOR",
    "JOB_REQUIRED_FIELDS",
    "MAX_PAGE_LIMIT",
    "RATE_CLASSES",
    "RESERVED_PACKAGES",
    "RULES",
    "RULES_DOC",
    "SUPPORTED_CONTRACTS",
    "ApiContractViolation",
    "operation_violations",
    "violation",
]
