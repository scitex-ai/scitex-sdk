#!/usr/bin/env python3
"""The wire of hosted MCP: HTTP request/response values and JSON-RPC shapes.

Framework-neutral: a host adapter (:mod:`._django`) turns its own request
into :class:`McpHttpRequest` and writes :class:`McpHttpResponse` back.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..api_exec import ApiCaller

#: Newest first; the first entry is offered when a client asks for another.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


@dataclass(frozen=True)
class McpHttpRequest:
    """One HTTP request to the MCP endpoint, as the host adapter read it.

    ``headers`` keys are lower-case. ``native`` is the host's own request
    object (a Django ``HttpRequest``), handed to the authenticator and the
    project resolver untouched. ``origin`` is the endpoint's own origin
    (``https://scitex.ai``), always an allowed ``Origin``.
    """

    method: str
    headers: Mapping[str, str]
    body: bytes = b""
    native: Any = None
    origin: str = ""


@dataclass(frozen=True)
class McpHttpResponse:
    """The answer: status, headers, body bytes."""

    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


@dataclass(frozen=True)
class McpHooks:
    """The host's side, per request: the same hooks REST serving uses.

    ``authenticate(request) -> ApiCaller | None`` is the pluggable
    authenticator (the REST ``SCITEX_API_CALLER`` contract);
    ``project_resolver(request) -> resolve(caller, project_id, write)``;
    ``rate_limiter.check(caller, operation, request)``;
    ``meter.record(event)``; ``idempotency_store.get/put`` (see
    :mod:`scitex_sdk.app.api_serve`).
    """

    authenticate: Callable[[Any], ApiCaller | None] | None
    project_resolver: Callable[[Any], Callable] | None = None
    rate_limiter: Any = None
    meter: Any = None
    idempotency_store: Any = None


class RpcError(Exception):
    """A JSON-RPC protocol error (unknown tool, malformed params, ...)."""

    def __init__(self, code: int, message: str, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def json_response(status: int, payload: Any, headers=None, ctype=None):
    out = {"Content-Type": ctype or "application/json"}
    out.update(headers or {})
    return McpHttpResponse(status, out, json.dumps(payload, default=str).encode())


def rpc_error(code: int, message: str, rpc_id=None, data=None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": rpc_id, "error": error}


__all__ = [
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "PARSE_ERROR",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "McpHooks",
    "McpHttpRequest",
    "McpHttpResponse",
    "RpcError",
    "json_response",
    "rpc_error",
]
