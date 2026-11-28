#!/usr/bin/env python3
"""Serve declared leaf operations under ``/api/v1/`` — generically, in any host.

A host adds ONE line to its URLconf::

    from scitex_sdk.app.api_serve import api_urlpatterns
    urlpatterns += api_urlpatterns()

and every installed ``scitex.apis`` plugin from a trusted distribution is
mounted at ``api/v1/<plugin-id>/`` with no plugin-specific host code. Each
request goes through :func:`.api_exec.execute`, so scopes, parameters, the
error envelope (RFC 9457 problem+json) and pagination are the same for every
leaf.

HOST HOOKS (Django settings; dotted paths or objects). The host owns all of
these; the leaf owns none:

``SCITEX_API_TRUSTED_DISTRIBUTIONS``
    fnmatch patterns of distributions whose plugins are admitted (default
    none — nothing is mounted until the host says so). Admission uses
    :func:`.api_mount.admit` with every declared route enabled.
``SCITEX_API_CALLER`` (required)
    ``caller(request) -> ApiCaller | None``: authenticate the request (token,
    OAuth bearer or session) and state its scopes. ``None`` -> 401. A host
    without one answers 503 for every non-public operation: an API nobody
    authenticates is not open, it is unconfigured.
``SCITEX_API_RATE_LIMITER`` (optional)
    ``check(caller, operation, request)``; raise :class:`ApiProblem` (429 with
    ``Retry-After``) to refuse.
``SCITEX_API_METER`` (optional)
    ``record(event: dict)`` after every call (operation, caller, status,
    duration, bytes; never bodies).
``SCITEX_API_IDEMPOTENCY_STORE`` (required for write operations)
    ``get(key) -> (digest, status, body) | None`` and
    ``put(key, digest, status, body)``. :class:`InMemoryIdempotencyStore` is
    a single-process store for tests and local hosts.

Project-scoped operations are authorized through
``scitex_sdk.host.project_access`` (the ``project`` parameter is
``owner/slug``). Session callers must pass CSRF on writes.
"""

from __future__ import annotations

import fnmatch
import json
import threading
import time
import uuid
from collections import OrderedDict

import scitex_logging as slogging

from .api_exec import ApiCaller, ApiProblem, ApiResult, execute, params_digest
from .api_ops import API_PREFIX, operation_of
from .api_plugin import ApiPluginContractError
from .api_tier import PRIORITY_HEADER, TieredCall, anonymous_caller, decide, run_tiered

PROBLEM_JSON = "application/problem+json"
_LOG = slogging.getLogger(__name__)


#: Plugins discovered but not mounted, with the reason (for host diagnostics).
REFUSED: dict = {}


class InMemoryIdempotencyStore:
    """A bounded single-process idempotency store (tests, local hosts)."""

    def __init__(self, capacity: int = 10_000):
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._capacity = capacity

    def get(self, key):
        with self._lock:
            return self._data.get(key)

    def put(self, key, digest, status, body):
        with self._lock:
            self._data[key] = (digest, status, body)
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)


class CacheIdempotencyStore:
    """Idempotency keys in the host's Django cache (shared across workers).

    Keys live ``timeout`` seconds (default 24 h, the replay window clients
    are promised). A host whose cache is per-process should use a shared
    backend (Redis) for this to hold across workers.
    """

    def __init__(self, timeout: int = 24 * 3600, alias: str = "default"):
        self.timeout = timeout
        self.alias = alias

    def _key(self, key) -> str:
        import hashlib

        return "scitex-api-idem:" + hashlib.sha256(repr(key).encode()).hexdigest()

    def get(self, key):
        from django.core.cache import caches

        value = caches[self.alias].get(self._key(key))
        return tuple(value) if value is not None else None

    def put(self, key, digest, status, body):
        from django.core.cache import caches

        caches[self.alias].set(self._key(key), (digest, status, body), self.timeout)


def _hook(name: str, *, required: bool = False):
    from .api_tier._profiles import hook

    return hook(name)


def _response(result: ApiResult):
    from django.http import HttpResponse

    if result.body is None:
        response = HttpResponse(status=result.status)
    else:
        problem = (
            result.status >= 400 and "code" in result.body and "type" in result.body
        )
        response = HttpResponse(
            json.dumps(result.body, default=str),
            status=result.status,
            content_type=PROBLEM_JSON if problem else "application/json",
        )
    for key, value in result.headers.items():
        response[key] = value
    return response


def _problem(problem: ApiProblem, request_id: str):
    return _response(
        ApiResult(problem.status, problem.body(request_id), problem.headers)
    )


def _body_size(request) -> int:
    """The body size; a body over the host's own cap is a 413 problem, not HTML."""
    from django.core.exceptions import RequestDataTooBig

    try:
        return len(request.body or b"")
    except RequestDataTooBig:
        raise ApiProblem(
            413,
            "api.request_too_large",
            "the request body exceeds this host's size limit",
            extra={"limit": "max_request_bytes"},
        ) from None


def _raw_params(request) -> dict:
    if request.method == "GET":
        return {k: request.GET.get(k) for k in request.GET}
    if request.content_type == "application/json":
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            raise ApiProblem(
                400, "api.invalid_body", "the body is not valid JSON"
            ) from None
        if not isinstance(body, dict):
            raise ApiProblem(400, "api.invalid_body", "the body must be a JSON object")
        return body
    return {k: request.POST.get(k) for k in request.POST}


def _project_resolver(request):
    def resolve(caller, project_id, write):
        from scitex_sdk.host import project_access

        query = request.GET.copy()
        query["project"] = project_id
        request.GET = query
        return project_access(request, write=write, remember=False)

    return resolve


def _csrf_ok(request) -> bool:
    from django.middleware.csrf import CsrfViewMiddleware

    reason = CsrfViewMiddleware(lambda r: None).process_view(request, None, (), {})
    return reason is None


def operation_view(plugin, route):
    """The Django view of one declared route."""
    from django.views.decorators.csrf import csrf_exempt

    op = operation_of(plugin, route)

    @csrf_exempt
    def view(request, **kwargs):
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        caller: ApiCaller | None = None
        tiered: TieredCall | None = None
        try:
            if request.method != op.method:
                raise ApiProblem(
                    405,
                    "api.method_not_allowed",
                    f"use {op.method}",
                    headers={"Allow": op.method},
                )
            caller_hook = _hook("SCITEX_API_CALLER")
            if caller_hook is None:
                raise ApiProblem(
                    503, "api.unavailable", "API authentication is not configured"
                )
            caller = caller_hook(request)
            presented = bool(request.headers.get("Authorization", "").strip())
            if caller is None and not presented:
                caller = anonymous_caller(op, request)
            if caller is None:
                raise ApiProblem(
                    401,
                    "api.unauthenticated",
                    "a valid token is required",
                    headers={"WWW-Authenticate": 'Bearer realm="scitex"'},
                )
            tiered = TieredCall(decide(op, caller, request))
            if (
                caller.via == "session"
                and op.access == "write"
                and not _csrf_ok(request)
            ):
                raise ApiProblem(403, "api.csrf_failed", "CSRF verification failed")
            limiter = _hook("SCITEX_API_RATE_LIMITER")
            if limiter is not None:
                limiter.check(caller, op, request)
            request_bytes = _body_size(request)
            raw = _raw_params(request)
            idem_key = None
            store = None
            if op.access == "write":
                header = request.headers.get("Idempotency-Key", "").strip()
                if not header:
                    raise ApiProblem(
                        400,
                        "api.idempotency_key_required",
                        "send an Idempotency-Key header",
                    )
                store = _hook("SCITEX_API_IDEMPOTENCY_STORE")
                if store is None:
                    raise ApiProblem(
                        503, "api.unavailable", "idempotency storage is not configured"
                    )
                idem_key = (caller.identity, op.operation_id, header)
                digest = params_digest({"params": raw, "id": kwargs})
                previous = store.get(idem_key)
                if previous is not None:
                    if previous[0] != digest:
                        raise ApiProblem(
                            409,
                            "api.idempotency_mismatch",
                            "this Idempotency-Key was used with other parameters",
                        )
                    return _response(
                        ApiResult(
                            previous[1], previous[2], {"Idempotent-Replayed": "true"}
                        )
                    )

            def run(decision):
                return execute(
                    op,
                    caller,
                    raw,
                    item_id=kwargs.get(op.id_param) if op.id_param else None,
                    resolve_project=_project_resolver(request),
                    request=request,
                    request_id=request_id,
                    tier=decision,
                )

            result, tiered = run_tiered(
                op,
                caller,
                request,
                run,
                request_bytes=request_bytes,
                tiered=tiered,
            )
            if store is not None and result.status < 500:
                store.put(idem_key, digest, result.status, result.body)
            response = _response(result)
        except ApiProblem as problem:
            response = _problem(problem, request_id)
        response["X-Request-Id"] = request_id
        # API-Q002: every response names the class the host assigned.
        response[PRIORITY_HEADER] = (
            tiered.decision.priority_class if tiered else "public"
        )
        meter = _hook("SCITEX_API_METER")
        if meter is not None:
            egress = len(getattr(response, "content", b"") or b"")
            event = {
                "request_id": request_id,
                "operation_id": op.operation_id,
                "package": op.package,
                "status": response.status_code,
                "duration_seconds": round(time.monotonic() - started, 6),
                "egress_bytes": egress,
                "caller": caller.identity if caller else None,
                "token_id": caller.token_id if caller else None,
                "user_id": getattr(getattr(caller, "user", None), "pk", None),
            }
            if tiered is not None:
                event.update(tiered.meter_fields(egress))
            meter.record(event)
        return response

    view.__name__ = op.mcp_name
    return view


def _dispatch(views: dict):
    """One URL, several declared methods: route by method, else 405 problem."""

    def view(request, **kwargs):
        handler = views.get(request.method)
        if handler is None:
            request_id = uuid.uuid4().hex
            allowed = ", ".join(sorted(views))
            response = _problem(
                ApiProblem(
                    405,
                    "api.method_not_allowed",
                    f"use {allowed}",
                    headers={"Allow": allowed},
                ),
                request_id,
            )
            response["X-Request-Id"] = request_id
            return response
        return handler(request, **kwargs)

    return view


def _django_route(path: str) -> str:
    return "/".join(
        f"<str:{segment[1:-1]}>" if segment.startswith("{") else segment
        for segment in path.split("/")
    )


def admitted_plugins(refs=None) -> list:
    """``(ref, plugin)`` for every plugin the host admits.

    ``refs`` given: the HOST chose them, and that list is its admission.
    ``refs`` omitted: every discovered plugin whose distribution matches
    ``SCITEX_API_TRUSTED_DISTRIBUTIONS``.
    """
    from django.conf import settings

    from .api_mount import AdmissionDenied, admit, resolve_handler
    from .api_plugin import discover_api_plugins

    patterns = tuple(getattr(settings, "SCITEX_API_TRUSTED_DISTRIBUTIONS", ()) or ())
    out = []
    explicit = refs is not None
    for ref in refs if explicit else discover_api_plugins():
        if not explicit and not any(
            fnmatch.fnmatch(ref.distribution, p) for p in patterns
        ):
            continue
        from importlib import import_module

        module, _, attr = ref.target.partition(":")
        plugin = getattr(import_module(module), attr)
        try:
            from .api_ops import operations
            from .api_rules import check_contract

            check_contract(plugin)
            operations(plugin)
        except ApiPluginContractError as exc:
            # Refused, not mounted: a plugin off the operation grammar would be
            # served with a shape no client was promised. Logged loudly (the
            # message carries the rule id); the rest of the host keeps serving,
            # and a host's CI asserts REFUSED is empty for its trusted set.
            _LOG.error("scitex.apis %s not mounted: %s", ref.name, exc)
            REFUSED[ref.name] = str(exc)
            continue
        admission = admit(
            ref,
            review_ref=(
                f"host-listed:{ref.name}"
                if explicit
                else f"trusted-distribution:{ref.distribution}"
            ),
            enabled=[route.path for route in plugin.routes],
        )
        for route in plugin.routes:
            try:
                resolve_handler(ref, admission, route.path, route.methods[0])
            except AdmissionDenied as exc:
                raise AdmissionDenied(f"{ref.name}: {exc}") from exc
        out.append((ref, plugin))
    return out


def _not_found(request, *args, **kwargs):
    """Any other ``api/v1/`` path: a problem, never the host's HTML 404 page.

    A path with a trailing slash is named with its canonical spelling
    (API-R004): v1 paths never end in ``/``, and saying so is cheaper for a
    client than a bare 404.
    """
    request_id = uuid.uuid4().hex
    path = request.path
    detail = "no such API operation"
    if path.endswith("/") and path.rstrip("/") != f"/{API_PREFIX}":
        detail = (
            f"no such API operation; v1 paths have no trailing slash "
            f"(API-R004): try {path.rstrip('/')}"
        )
    response = _problem(ApiProblem(404, "api.not_found", detail), request_id)
    response["X-Request-Id"] = request_id
    return response


def api_urlpatterns(refs=None, *, catch_all: bool = True) -> list:
    """URL patterns for every admitted plugin, at ``api/v1/<plugin-id>/``.

    ``catch_all`` appends a problem+json 404 for every other ``api/v1/``
    path; a host that serves its own v1 routes passes ``False`` and appends
    :func:`api_not_found_pattern` after them.
    """
    from django.urls import path
    from django.views.decorators.csrf import csrf_exempt

    patterns = []
    for _ref, plugin in admitted_plugins(refs):
        by_path: dict = {}
        for route in plugin.routes:
            by_path.setdefault(route.path, []).append(route)
        # A literal segment must win over a parameter in the same position
        # (``tests/recommend`` before ``tests/{test_id}``): Django takes the
        # first match, so mount the paths with fewer parameters first.
        ordered = sorted(by_path.items(), key=lambda item: item[0].count("{"))
        for route_path, routes in ordered:
            views = {r.methods[0]: operation_view(plugin, r) for r in routes}
            names = "+".join(operation_of(plugin, r).mcp_name for r in routes)
            patterns.append(
                path(
                    f"{API_PREFIX}/{plugin.id}/{_django_route(route_path)}",
                    csrf_exempt(_dispatch(views)),
                    name=f"api-{names}",
                )
            )
    if catch_all:
        patterns.append(api_not_found_pattern())
    return patterns


def api_not_found_pattern():
    """The problem+json 404 for unmatched ``api/v1/`` paths."""
    from django.urls import re_path
    from django.views.decorators.csrf import csrf_exempt

    return re_path(rf"^{API_PREFIX}/", csrf_exempt(_not_found), name="api-not-found")


__all__ = [
    "PROBLEM_JSON",
    "REFUSED",
    "CacheIdempotencyStore",
    "InMemoryIdempotencyStore",
    "admitted_plugins",
    "api_not_found_pattern",
    "api_urlpatterns",
    "operation_view",
]
