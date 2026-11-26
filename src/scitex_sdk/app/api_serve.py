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

from .api_exec import ApiCaller, ApiProblem, ApiResult, execute, params_digest
from .api_ops import API_PREFIX, operation_of

PROBLEM_JSON = "application/problem+json"


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


def _hook(name: str, *, required: bool = False):
    from django.conf import settings
    from django.utils.module_loading import import_string

    value = getattr(settings, name, None)
    if value is None:
        return None
    if isinstance(value, str):
        value = import_string(value)
    return value() if isinstance(value, type) else value


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
            if caller is None:
                raise ApiProblem(
                    401,
                    "api.unauthenticated",
                    "a valid token is required",
                    headers={"WWW-Authenticate": 'Bearer realm="scitex"'},
                )
            if (
                caller.via == "session"
                and op.access == "write"
                and not _csrf_ok(request)
            ):
                raise ApiProblem(403, "api.csrf_failed", "CSRF verification failed")
            limiter = _hook("SCITEX_API_RATE_LIMITER")
            if limiter is not None:
                limiter.check(caller, op, request)
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
            result = execute(
                op,
                caller,
                raw,
                item_id=kwargs.get(op.id_param) if op.id_param else None,
                resolve_project=_project_resolver(request),
                request=request,
                request_id=request_id,
            )
            if store is not None and result.status < 500:
                store.put(idem_key, digest, result.status, result.body)
            response = _response(result)
        except ApiProblem as problem:
            response = _problem(problem, request_id)
        response["X-Request-Id"] = request_id
        meter = _hook("SCITEX_API_METER")
        if meter is not None:
            meter.record(
                {
                    "request_id": request_id,
                    "operation_id": op.operation_id,
                    "package": op.package,
                    "status": response.status_code,
                    "duration_seconds": round(time.monotonic() - started, 6),
                    "egress_bytes": len(getattr(response, "content", b"") or b""),
                    "caller": caller.identity if caller else None,
                    "token_id": caller.token_id if caller else None,
                }
            )
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
                ApiProblem(405, "api.method_not_allowed", f"use {allowed}",
                           headers={"Allow": allowed}),
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
    """Any other ``api/v1/`` path: a problem, never the host's HTML 404 page."""
    request_id = uuid.uuid4().hex
    response = _problem(ApiProblem(404, "api.not_found", "no such API operation"), request_id)
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
        for route_path, routes in by_path.items():
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
    "InMemoryIdempotencyStore",
    "admitted_plugins",
    "api_not_found_pattern",
    "api_urlpatterns",
    "operation_view",
]
