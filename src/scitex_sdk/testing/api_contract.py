#!/usr/bin/env python3
"""The SciTeX API contract test every leaf and the Hub run in CI.

One line in a leaf's test suite::

    from scitex_sdk.testing.api_contract import assert_contract
    from my_leaf._rest import PLUGIN

    def test_api_contract():
        assert_contract(PLUGIN)

It fails with every violation, each tagged with its rule id from
``docs/design/api-contract-v1/01-rules.md``:

* **static** (:func:`check_plugin`): every operation re-validated against the
  declaration rules, MCP tools 1:1 with operations (API-T002), and the OpenAPI
  document generated and valid (API-O001/O002);
* **served** (:func:`run_contract_suite`): the plugin is admitted and mounted
  through the real SDK serving path (``api_urlpatterns``) and every operation
  is called over HTTP with no credential and an invalid one (401 problem,
  API-A002/E001), with a credential lacking the scope (403, API-A003), with a
  method it does not declare (405 problem, API-V005), and, for writes, without
  an ``Idempotency-Key`` (400, API-I001). Every response must carry
  ``X-Request-Id`` (API-H001). Handlers never run: the probes stop at the
  shared envelope, so the suite has no side effects on the leaf's stores;
* **compatibility** (:func:`compare`, with ``previous=``): additive-only change
  against the last released declaration (API-C001).
"""

from __future__ import annotations

import json
import types
import uuid
from dataclasses import dataclass

from scitex_sdk.app.api_exec import ApiCaller
from scitex_sdk.app.api_mcp import tool_specs
from scitex_sdk.app.api_ops import operations
from scitex_sdk.app.api_plugin import (
    ApiPlugin,
    ApiPluginContractError,
    ApiPluginRef,
    discover_api_plugins,
)
from scitex_sdk.app.api_rules import check_contract, operation_violations
from scitex_sdk.app.api_verbs import (
    find_dictionary,
    read_verb_exceptions,
    verb_violations,
)

PROBLEM_JSON = "application/problem+json"
_PROBE_ID = "contract-probe-id"
_TOKENS = {"contract-no-scope": (), "contract-all-scopes": ("*",)}


@dataclass(frozen=True)
class Violation:
    """One contract failure."""

    rule: str
    operation_id: str
    message: str

    def __str__(self) -> str:
        where = f"{self.operation_id}: " if self.operation_id else ""
        return f"[{self.rule}] {where}{self.message}"


# ---------------------------------------------------------------- static


def check_plugin(plugin: ApiPlugin, *, verb_exceptions: dict | None = None) -> list:
    """Static violations of ``plugin`` (no Django needed)."""
    return declaration_violations(
        plugin, verb_exceptions=verb_exceptions
    ) + _openapi_violations(plugin)


def _verb_exceptions(given: dict | None) -> dict:
    """The package's ``verb_exceptions:`` (API-V003), from the project at cwd."""
    if given is not None:
        return given
    path = find_dictionary()
    return read_verb_exceptions(path) if path is not None else {}


def declaration_violations(
    plugin: ApiPlugin, *, verb_exceptions: dict | None = None
) -> list:
    """Operation grammar, verb, contract and MCP 1:1 violations, from the declaration.

    This is the subset the source-only Dev audit (``PS-SDK-API``) reports. A
    plugin whose routes were not built from operations fails API-D001.
    ``verb_exceptions`` (``{verb: has_why}``) defaults to the
    ``.scitex/dev/cli-audit-dict.yaml`` of the project the test runs in.
    """
    try:
        check_contract(plugin)
    except ApiPluginContractError as exc:
        return [Violation("API-D003", plugin.id, getattr(exc, "detail", str(exc)))]
    try:
        ops = operations(plugin)
    except ApiPluginContractError as exc:
        # An operation-built plugin always reads back; one that does not was
        # hand-written (or altered), whatever grammar rule it trips first.
        return [
            Violation(
                "API-D001",
                plugin.id,
                f"routes are not SDK operations (declare them with ApiOperation): {exc}",
            )
        ]
    out = []
    for op in ops:
        out.extend(
            Violation(r, op.operation_id, m) for r, m in operation_violations(op)
        )
    out.extend(
        Violation(r, oid, m)
        for r, oid, m in verb_violations(ops, _verb_exceptions(verb_exceptions))
    )
    specs = {spec.name: spec for spec in tool_specs(plugin)}
    if sorted(specs) != sorted(op.mcp_name for op in ops):
        out.append(Violation("API-T002", plugin.id, "MCP tools differ from operations"))
    for op in ops:
        spec = specs.get(op.mcp_name)
        if spec is None:
            continue
        expected = {f.name for f in op.request_fields()} | (
            {op.id_param} if op.id_param else set()
        )
        if set(spec.input_schema["properties"]) != expected:
            out.append(
                Violation(
                    "API-T002",
                    op.operation_id,
                    f"MCP input schema {sorted(spec.input_schema['properties'])} != "
                    f"request fields {sorted(expected)}",
                )
            )
    return out


def openapi_document(plugin: ApiPlugin) -> dict:
    """A complete OpenAPI 3.1 document for one plugin (served under its mount)."""
    fragment = plugin.openapi_fragment()
    return {
        "openapi": "3.1.0",
        "info": {"title": plugin.title, "version": plugin.api_version},
        "servers": [{"url": f"/api/v1/{plugin.id}"}],
        **fragment,
    }


def _openapi_violations(plugin: ApiPlugin) -> list:
    try:
        document = openapi_document(plugin)
    except ApiPluginContractError as exc:
        return [Violation("API-O001", plugin.id, str(exc))]
    try:
        from openapi_spec_validator import validate
    except ImportError:
        return [
            Violation(
                "API-O002",
                plugin.id,
                "openapi-spec-validator is not installed; add it to the test dependencies",
            )
        ]
    try:
        validate(document)
    except Exception as exc:  # noqa: BLE001 - the validator's own error types
        return [Violation("API-O002", plugin.id, f"invalid OpenAPI: {exc}")]
    return []


# ---------------------------------------------------------------- compatibility


def _shape(op) -> dict:
    return {
        "method": op.method,
        "path": op.path,
        "scope": op.scope,
        "async": op.is_async,
        "project_scoped": op.project_scoped,
        "required": {f.name for f in op.request_fields() if f.required},
        "params": {f.name for f in op.request_fields()},
        "response": {f.name for f in op.response.fields} if op.response else set(),
    }


def compare(previous: ApiPlugin, current: ApiPlugin) -> list:
    """API-C001: ``current`` may only add to ``previous``."""
    before = {op.operation_id: _shape(op) for op in operations(previous)}
    after = {op.operation_id: _shape(op) for op in operations(current)}
    out = []
    for oid, old in before.items():
        new = after.get(oid)
        if new is None:
            out.append(Violation("API-C001", oid, "operation removed"))
            continue
        for key in ("method", "path", "scope", "async", "project_scoped"):
            if old[key] != new[key]:
                out.append(
                    Violation(
                        "API-C001", oid, f"{key} changed {old[key]!r} -> {new[key]!r}"
                    )
                )
        if old["params"] - new["params"]:
            out.append(
                Violation(
                    "API-C001",
                    oid,
                    f"parameters removed {sorted(old['params'] - new['params'])}",
                )
            )
        newly_required = new["required"] - old["required"]
        if newly_required:
            out.append(
                Violation(
                    "API-C001",
                    oid,
                    f"parameters became required {sorted(newly_required)}",
                )
            )
        if old["response"] - new["response"]:
            out.append(
                Violation(
                    "API-C001",
                    oid,
                    f"response fields removed {sorted(old['response'] - new['response'])}",
                )
            )
    return out


# ---------------------------------------------------------------- served


def contract_caller(request):
    """The suite's ``SCITEX_API_CALLER``: two fixed tokens, nothing else."""
    from types import SimpleNamespace

    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token not in _TOKENS:
        return None
    user = SimpleNamespace(username="contract", pk="contract", is_authenticated=True)
    return ApiCaller(user=user, scopes=_TOKENS[token], via="token", token_id=token)


def _ensure_django():
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=False,
            SECRET_KEY="scitex-sdk-api-contract",
            ALLOWED_HOSTS=["testserver"],
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
            DATABASES={
                "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
            },
            MIDDLEWARE=[],
        )
        import django

        django.setup()


def _ref_for(plugin: ApiPlugin, target: str | None) -> ApiPluginRef:
    if target is not None:
        return ApiPluginRef(name=plugin.id, target=target, distribution="")
    for ref in discover_api_plugins():
        if ref.name == plugin.id:
            return ref
    raise LookupError(
        f"no installed scitex.apis entry point named {plugin.id!r}; install the "
        "package (pip install -e .) or pass target='module:PLUGIN'"
    )


def _url(op) -> str:
    path = (
        op.path.replace("{" + op.id_param + "}", _PROBE_ID) if op.id_param else op.path
    )
    return f"/api/v1/{op.package}/{path}"


def _call(client, method, url, token=None, key=None):
    headers = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if key:
        headers["HTTP_IDEMPOTENCY_KEY"] = key
    if method == "GET":
        return client.get(url, **headers)
    return client.generic(
        method, url, json.dumps({}), content_type="application/json", **headers
    )


def _expect(response, status, code, rule, oid, out, what):
    body = {}
    if response.get("Content-Type") == PROBLEM_JSON:
        try:
            body = json.loads(response.content)
        except ValueError:
            body = {}
    if response.status_code != status or response.get("Content-Type") != PROBLEM_JSON:
        out.append(
            Violation(
                rule,
                oid,
                f"{what}: expected {status} {PROBLEM_JSON}, got {response.status_code} "
                f"{response.get('Content-Type')}",
            )
        )
    elif code and body.get("code") != code:
        out.append(
            Violation(
                rule, oid, f"{what}: expected code {code}, got {body.get('code')}"
            )
        )
    if not response.get("X-Request-Id"):
        out.append(Violation("API-H001", oid, f"{what}: no X-Request-Id"))


def run_contract_suite(plugin: ApiPlugin, *, target: str | None = None) -> list:
    """Served violations: the plugin mounted and probed through the SDK host path."""
    _ensure_django()
    from django.test import Client, override_settings

    from scitex_sdk.app.api_serve import InMemoryIdempotencyStore, api_urlpatterns

    urlconf = types.ModuleType("scitex_sdk_api_contract_urls")
    urlconf.urlpatterns = api_urlpatterns([_ref_for(plugin, target)])
    out = []
    with override_settings(
        ROOT_URLCONF=urlconf,
        SCITEX_API_CALLER=contract_caller,
        SCITEX_API_IDEMPOTENCY_STORE=InMemoryIdempotencyStore(),
        SCITEX_API_RATE_LIMITER=None,
        SCITEX_API_METER=None,
    ):
        client = Client()
        for op in operations(plugin):
            oid, url = op.operation_id, _url(op)
            key = uuid.uuid4().hex if op.access == "write" else None
            # A public read (API-A004) is callable without a credential; its
            # anonymous and scope probes would run the handler, so they are
            # skipped. A presented-but-invalid bearer is a 401 either way.
            if not op.public:
                response = _call(client, op.method, url)
                _expect(
                    response,
                    401,
                    "api.unauthenticated",
                    "API-A002",
                    oid,
                    out,
                    "no credential",
                )
                if not response.get("WWW-Authenticate", "").startswith("Bearer"):
                    out.append(
                        Violation(
                            "API-A002", oid, "401 without WWW-Authenticate: Bearer"
                        )
                    )
            response = _call(client, op.method, url, token="contract-invalid")
            _expect(
                response,
                401,
                "api.unauthenticated",
                "API-A002",
                oid,
                out,
                "invalid bearer",
            )
            if not op.public:
                response = _call(
                    client, op.method, url, token="contract-no-scope", key=key
                )
                _expect(
                    response,
                    403,
                    "api.insufficient_scope",
                    "API-A003",
                    oid,
                    out,
                    "missing scope",
                )
            response = _call(client, "PUT", url, token="contract-all-scopes")
            _expect(
                response,
                405,
                "api.method_not_allowed",
                "API-V005",
                oid,
                out,
                "undeclared method",
            )
            if op.access == "write":
                response = _call(client, op.method, url, token="contract-all-scopes")
                _expect(
                    response,
                    400,
                    "api.idempotency_key_required",
                    "API-I001",
                    oid,
                    out,
                    "write without Idempotency-Key",
                )
    return out


def assert_contract(
    plugin: ApiPlugin,
    *,
    target: str | None = None,
    previous: ApiPlugin | None = None,
    verb_exceptions: dict | None = None,
) -> None:
    """Fail with every violation of ``plugin`` (static, served, compatibility)."""
    found = check_plugin(plugin, verb_exceptions=verb_exceptions)
    if not found:
        found = run_contract_suite(plugin, target=target)
    if previous is not None:
        found.extend(compare(previous, plugin))
    if found:
        lines = "\n".join(f"  {v}" for v in found)
        raise AssertionError(
            f"API contract violations in plugin {plugin.id!r} ({len(found)}):\n{lines}"
        )


__all__ = [
    "Violation",
    "assert_contract",
    "check_plugin",
    "compare",
    "contract_caller",
    "declaration_violations",
    "openapi_document",
    "run_contract_suite",
]
