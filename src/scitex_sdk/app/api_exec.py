#!/usr/bin/env python3
"""Run one declared operation — the transport-neutral core of REST and MCP.

:func:`execute` is the ONE place an operation call is checked and shaped:
scope against the caller's grant, parameters against the declared request
schema, the project id against the host's authorization, then the leaf's
handler, then the shared result envelope. The REST adapter
(:mod:`.api_serve`) and the MCP generator (:mod:`.api_mcp`) both call it, so
a REST operation and its MCP tool cannot drift apart.

What it deliberately does NOT do — the host's, via hooks: authenticate
(who the caller is and what the token grants), rate-limit, meter, and store
idempotency keys durably. The leaf's handler never sees any of that.

Handler contract::

    def handler(call: ApiCall) -> dict | list | ApiPage | ApiJob | None

``call.params`` are validated and typed; ``call.project`` is the host's
:class:`~scitex_sdk.host.ProjectAccess` for project-scoped operations;
``call.offset``/``call.limit`` drive a paginated list. A handler refuses
with :class:`ApiProblem`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .api_ops import ApiOperation, scope_granted

PROBLEM_TYPE_BASE = "https://scitex.ai/problems/"


class ApiProblem(Exception):
    """An RFC 9457 problem: ``status``, machine ``code``, human ``detail``."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        *,
        title: str = "",
        retryable: bool = False,
        errors: Sequence[Mapping[str, str]] = (),
        headers: Mapping[str, str] | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(detail)
        self.status = int(status)
        self.code = code
        self.detail = detail
        self.title = title or code.rsplit(".", 1)[-1].replace("_", " ").capitalize()
        self.retryable = retryable
        self.errors = list(errors)
        self.headers = dict(headers or {})
        self.extra = dict(extra or {})

    def body(self, request_id: str) -> dict:
        body = {
            "type": PROBLEM_TYPE_BASE + self.code,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
            "request_id": request_id,
            "retryable": self.retryable,
            "errors": self.errors,
        }
        body.update(self.extra)
        return body


@dataclass(frozen=True)
class ApiCaller:
    """Who is calling, as the HOST resolved it (never the leaf).

    ``via`` is ``token`` (a personal/project token or OAuth bearer) or
    ``session`` (a browser session cookie). ``project`` restricts a project
    token to one ``owner/slug``. ``tier`` is the account tier the host
    assigned (``public`` < ``member`` < ``paid``, API-Q001); it is never
    taken from a request parameter.
    """

    user: Any
    scopes: tuple = ()
    via: str = "token"
    token_id: str | None = None
    project: str | None = None
    tier: str = "member"

    @property
    def identity(self) -> str:
        name = getattr(self.user, "pk", None) or getattr(self.user, "username", "")
        return f"{self.via}:{self.token_id or name}"


@dataclass
class ApiPage:
    """One page of a paginated list."""

    items: list
    has_more: bool
    total: int | None = None


@dataclass
class ApiJob:
    """An accepted asynchronous operation (HTTP 202)."""

    job: dict


@dataclass
class ApiCall:
    """What a handler receives."""

    operation: ApiOperation
    caller: ApiCaller
    params: dict
    id: str | None = None
    project: Any = None
    request: Any = None
    offset: int = 0
    limit: int = 0
    request_id: str = ""


@dataclass(frozen=True)
class ApiResult:
    """A transport-neutral answer: HTTP-style status, JSON body, headers."""

    status: int
    body: dict | None
    headers: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# parameters
# --------------------------------------------------------------------------

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _coerce(value: Any, kind: str, name: str) -> Any:
    def bad():
        return ApiProblem(
            400,
            "api.invalid_parameter",
            f"parameter {name!r} must be {kind}",
            errors=[{"field": name, "code": "invalid", "message": f"expected {kind}"}],
        )

    if kind == "string":
        if not isinstance(value, str):
            raise bad()
        return value
    if kind == "integer":
        if isinstance(value, bool):
            raise bad()
        try:
            return int(value)
        except (TypeError, ValueError):
            raise bad() from None
    if kind == "number":
        if isinstance(value, bool):
            raise bad()
        try:
            return float(value)
        except (TypeError, ValueError):
            raise bad() from None
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in _TRUE | _FALSE:
            return value.lower() in _TRUE
        raise bad()
    if kind in ("object", "array"):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise bad() from None
        expected = dict if kind == "object" else list
        if not isinstance(value, expected):
            raise bad()
        return value
    raise bad()  # pragma: no cover - FIELD_TYPES is closed


def validate_params(op: ApiOperation, raw: Mapping[str, Any]) -> dict:
    """Declared fields only, typed; missing required and unknown ones refused."""
    fields = {f.name: f for f in op.request_fields()}
    unknown = sorted(set(raw) - set(fields))
    if unknown:
        raise ApiProblem(
            400,
            "api.unknown_parameter",
            f"unknown parameter(s): {', '.join(unknown)}",
            errors=[
                {"field": n, "code": "unknown", "message": "not declared"}
                for n in unknown
            ],
        )
    params = {}
    missing = []
    for name, spec in fields.items():
        value = raw.get(name)
        if value is None or value == "":
            if spec.required:
                missing.append(name)
            continue
        value = _coerce(value, spec.type, name)
        if spec.enum and value not in spec.enum:
            raise ApiProblem(
                400,
                "api.invalid_parameter",
                f"parameter {name!r} must be one of {', '.join(spec.enum)}",
                errors=[{"field": name, "code": "enum", "message": "not allowed"}],
            )
        params[name] = value
    if missing:
        raise ApiProblem(
            400,
            "api.missing_parameter",
            f"missing required parameter(s): {', '.join(missing)}",
            errors=[
                {"field": n, "code": "required", "message": "required"} for n in missing
            ],
        )
    return params


def encode_cursor(offset: int) -> str:
    raw = json.dumps({"o": int(offset)}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        offset = int(json.loads(base64.urlsafe_b64decode(padded))["o"])
    except (ValueError, KeyError, TypeError):
        raise ApiProblem(400, "api.invalid_cursor", "the cursor is not valid") from None
    if offset < 0:
        raise ApiProblem(400, "api.invalid_cursor", "the cursor is not valid")
    return offset


def params_digest(params: Mapping[str, Any]) -> str:
    """A stable digest of validated parameters (idempotency mismatch check)."""
    return hashlib.sha256(
        json.dumps(params, sort_keys=True, default=str).encode()
    ).hexdigest()


# --------------------------------------------------------------------------
# host exceptions -> problems
# --------------------------------------------------------------------------


def problem_from(exc: BaseException) -> ApiProblem:
    """The shared problem for a host or leaf exception; never a traceback."""
    if isinstance(exc, ApiProblem):
        return exc
    from scitex_sdk.host import AccessError, CapabilityUnavailable, StorageRefused

    if isinstance(exc, StorageRefused):
        return ApiProblem(
            exc.status,
            f"host.{exc.code or 'storage_refused'}".replace("-", "_"),
            str(exc),
            extra={"link": exc.link} if exc.link else None,
        )
    if isinstance(exc, AccessError):
        status = getattr(exc, "status", 400)
        codes = {401: "api.unauthenticated", 403: "api.forbidden", 404: "api.not_found"}
        # One answer for "absent" and "not yours".
        detail = "not found" if status == 404 else str(exc)
        return ApiProblem(status, codes.get(status, "api.bad_request"), detail)
    if isinstance(exc, CapabilityUnavailable):
        return ApiProblem(
            503, "api.unavailable", str(exc) or "unavailable", retryable=True
        )
    leaf_status = getattr(exc, "status", None)
    if isinstance(leaf_status, int) and 400 <= leaf_status < 500:
        return ApiProblem(leaf_status, "api.rejected", str(exc))
    return ApiProblem(500, "api.internal_error", "the operation failed", retryable=True)


# --------------------------------------------------------------------------
# execute
# --------------------------------------------------------------------------

ProjectResolver = Callable[[ApiCaller, str, bool], Any]


def execute(
    op: ApiOperation,
    caller: ApiCaller,
    raw_params: Mapping[str, Any],
    *,
    item_id: str | None = None,
    resolve_project: ProjectResolver | None = None,
    request: Any = None,
    request_id: str | None = None,
    handler: Callable | None = None,
) -> ApiResult:
    """Run ``op`` for ``caller``; every failure becomes a problem result.

    ``handler`` defaults to importing ``op.handler``; ``resolve_project`` is
    the host's project authorization (required for project-scoped
    operations).
    """
    request_id = request_id or uuid.uuid4().hex
    try:
        if not op.public and not scope_granted(op.scope, caller.scopes):
            raise ApiProblem(
                403,
                "api.insufficient_scope",
                f"this operation needs the scope {op.scope}",
                extra={"required_scope": op.scope},
            )
        params = validate_params(op, raw_params)
        call = ApiCall(
            operation=op,
            caller=caller,
            params=params,
            id=item_id,
            request=request,
            request_id=request_id,
        )
        if op.project_scoped:
            project_id = params.pop("project")
            if caller.project and caller.project != project_id:
                raise ApiProblem(
                    403, "api.forbidden", "this token is restricted to another project"
                )
            if resolve_project is None:
                raise ApiProblem(
                    503, "api.unavailable", "project access is unavailable"
                )
            call.project = resolve_project(caller, project_id, op.access == "write")
        if op.paginated:
            limit = params.pop("limit", op.default_limit)
            if not 1 <= limit <= op.max_limit:
                raise ApiProblem(
                    400,
                    "api.invalid_parameter",
                    f"limit must be between 1 and {op.max_limit}",
                    errors=[
                        {"field": "limit", "code": "range", "message": "out of range"}
                    ],
                )
            call.limit = limit
            call.offset = decode_cursor(params.pop("cursor", None))
        target = handler or _import(op.handler)
        result = target(call)
        return _shape(op, call, result)
    except Exception as exc:  # noqa: BLE001 - the one problem boundary
        problem = problem_from(exc)
        return ApiResult(problem.status, problem.body(request_id), problem.headers)


def _shape(op: ApiOperation, call: ApiCall, result: Any) -> ApiResult:
    if isinstance(result, ApiJob):
        return ApiResult(202, {"job": result.job})
    if op.paginated:
        if not isinstance(result, ApiPage):
            raise TypeError(f"{op.operation_id} must return an ApiPage")
        body = {
            "data": list(result.items),
            "has_more": bool(result.has_more),
            "next_cursor": (
                encode_cursor(call.offset + len(result.items))
                if result.has_more
                else None
            ),
        }
        if result.total is not None:
            body["total"] = result.total
        return ApiResult(200, body)
    if op.verb == "delete" and result is None:
        return ApiResult(204, None)
    return ApiResult(op.success_status, {"data": result})


def _import(target: str) -> Callable:
    from importlib import import_module

    module, _, attr = target.partition(":")
    obj: Any = import_module(module)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


__all__ = [
    "ApiCall",
    "ApiCaller",
    "ApiJob",
    "ApiPage",
    "ApiProblem",
    "ApiResult",
    "decode_cursor",
    "encode_cursor",
    "execute",
    "params_digest",
    "problem_from",
    "validate_params",
]
