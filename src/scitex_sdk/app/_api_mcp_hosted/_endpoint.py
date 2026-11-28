#!/usr/bin/env python3
"""The hosted MCP endpoint: Streamable HTTP transport and JSON-RPC dispatch.

Transport (MCP specification 2025-11-25; 2025-06-18 and 2025-03-26 clients
are answered too): one endpoint, ``POST`` only, one JSON-RPC message per
request, answered with ``application/json``. The server is stateless: it
issues no ``Mcp-Session-Id`` and opens no SSE stream (``GET`` is 405), so
any worker can answer any request. Long work is a Job (API-J001), not a
stream. The protocol surface is ``initialize``, ``ping``, ``tools/list`` and
``tools/call``.

Checks, in order: ``Origin`` (403, DNS-rebinding defence), method (405),
``Accept`` (406), credential (401 + ``WWW-Authenticate``),
``MCP-Protocol-Version`` (400), then the JSON-RPC message.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Mapping, Sequence

from ..api_exec import ApiCaller, ApiProblem, problem_from
from ..api_mcp import McpToolSpec, tool_specs
from ..api_plugin import ApiPluginContractError
from ._call import call_hosted_tool
from ._policy import anonymous_caller, denial, resolve_tiers
from ._wire import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    SUPPORTED_PROTOCOL_VERSIONS,
    McpHooks,
    McpHttpRequest,
    McpHttpResponse,
    RpcError,
    json_response,
    rpc_error,
)


def _sdk_version() -> str:
    try:
        from scitex_sdk import __version__
    except Exception:  # noqa: BLE001 - a version string is cosmetic
        return "0"
    return str(__version__)


class HostedMcp:
    """The hosted MCP endpoint over ``plugins`` (admitted ``ApiPlugin``).

    ``hooks`` are the default host hooks (:class:`McpHooks`); a host that
    reads them per request passes them to :meth:`handle` instead.
    ``tool_tiers`` raises tools' tiers (see :mod:`._policy`). ``anonymous``
    lets a request without a credential in as a ``public``-tier caller (it
    sees public tools only); otherwise such a request gets the 401
    challenge that starts OAuth discovery. ``resource_metadata_url`` is the
    RFC 9728 document that challenge names. ``allowed_origins`` extends the
    endpoint's own origin for the ``Origin`` check (``"*"`` allows any).
    """

    def __init__(
        self,
        plugins: Iterable,
        *,
        hooks: McpHooks | None = None,
        tool_tiers: Mapping[str, str] | None = None,
        anonymous: bool = False,
        resource_metadata_url: str | None = None,
        allowed_origins: Sequence[str] = (),
        server_name: str = "scitex",
        server_version: str | None = None,
        instructions: str | None = None,
    ):
        self.plugins = tuple(plugins)
        self.hooks = hooks
        self.anonymous = bool(anonymous)
        self.resource_metadata_url = resource_metadata_url
        self.allowed_origins = tuple(o.rstrip("/") for o in allowed_origins)
        self.server_name = server_name
        self.server_version = server_version or _sdk_version()
        self.instructions = instructions
        self.specs: dict[str, McpToolSpec] = {}
        for plugin in self.plugins:
            for spec in tool_specs(plugin):
                if spec.name in self.specs:
                    raise ApiPluginContractError(
                        f"[API-T001] tool {spec.name!r} is declared by two "
                        "plugins; hosted tool names must be unique"
                    )
                self.specs[spec.name] = spec
        self.tiers = resolve_tiers(self.specs, tool_tiers or {})

    # ------------------------------------------------------------- policy
    def tier_of(self, name: str) -> str:
        """The account tier a caller needs to see and call tool ``name``."""
        return self.tiers[name]

    def tools_for(self, caller: ApiCaller) -> list:
        """The tools ``caller`` may see: scope- and tier-filtered (API-M002)."""
        return [
            spec
            for name, spec in self.specs.items()
            if denial(caller, spec, self.tiers[name]) is None
        ]

    def tool_json(self, spec: McpToolSpec, caller: ApiCaller) -> dict:
        """The ``tools/list`` entry of ``spec`` as ``caller`` sees it."""
        schema = spec.input_schema
        if spec.operation.project_scoped and caller.project:
            # A project token's tools default `project` to its project.
            schema = dict(schema)
            schema["required"] = [r for r in schema["required"] if r != "project"]
        tool = {
            "name": spec.name,
            "title": spec.title,
            "description": spec.description,
            "inputSchema": schema,
        }
        if spec.output_schema is not None:
            tool["outputSchema"] = spec.output_schema
        if spec.annotations:
            tool["annotations"] = spec.annotations
        return tool

    # ---------------------------------------------------------- transport
    def handle(
        self, request: McpHttpRequest, hooks: McpHooks | None = None
    ) -> McpHttpResponse:
        """Answer one HTTP request to the endpoint."""
        hooks = hooks or self.hooks or McpHooks(authenticate=None)
        request_id = uuid.uuid4().hex
        response = self._handle(request, hooks, request_id)
        response.headers.setdefault("X-Request-Id", request_id)
        return response

    def _handle(self, request, hooks, request_id) -> McpHttpResponse:
        headers = request.headers
        origin = headers.get("origin", "").rstrip("/")
        if origin and not self._origin_ok(origin, request.origin):
            return json_response(
                403, rpc_error(INVALID_REQUEST, f"origin {origin!r} is not allowed")
            )
        if request.method != "POST":
            # Stateless: no server-to-client SSE stream, no session to delete.
            return McpHttpResponse(405, {"Allow": "POST"})
        accept = headers.get("accept", "")
        if accept and not any(
            t in accept for t in ("application/json", "*/*", "application/*")
        ):
            return json_response(
                406, rpc_error(INVALID_REQUEST, "accept application/json")
            )
        try:
            caller = self._authenticate(request, hooks)
        except ApiProblem as problem:
            return json_response(
                problem.status,
                problem.body(request_id),
                problem.headers,
                ctype="application/problem+json",
            )
        version = headers.get("mcp-protocol-version", "")
        if version and version not in SUPPORTED_PROTOCOL_VERSIONS:
            return json_response(
                400,
                rpc_error(
                    INVALID_REQUEST,
                    f"unsupported MCP-Protocol-Version {version!r}",
                    data={"supported": list(SUPPORTED_PROTOCOL_VERSIONS)},
                ),
            )
        try:
            message = json.loads(request.body or b"")
        except (ValueError, UnicodeDecodeError):
            return json_response(400, rpc_error(PARSE_ERROR, "parse error"))
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return json_response(
                400, rpc_error(INVALID_REQUEST, "one JSON-RPC 2.0 message per POST")
            )
        if "method" not in message:
            if "result" in message or "error" in message:
                return McpHttpResponse(202)  # a response to us: nothing asked
            return json_response(400, rpc_error(INVALID_REQUEST, "no method"))
        if "id" not in message:
            return McpHttpResponse(202)  # a notification, e.g. initialized
        rpc_id = message["id"]
        if not isinstance(rpc_id, (str, int)) or isinstance(rpc_id, bool):
            return json_response(
                400, rpc_error(INVALID_REQUEST, "id must be a string or number")
            )
        params = message.get("params") or {}
        out_headers: dict = {}
        try:
            if not isinstance(params, dict):
                raise RpcError(INVALID_PARAMS, "params must be an object")
            result = self._dispatch(
                message["method"], params, rpc_id, caller, request, hooks, out_headers
            )
            payload = {"jsonrpc": "2.0", "id": rpc_id, "result": result}
        except RpcError as err:
            payload = rpc_error(err.code, err.message, rpc_id, err.data)
        return json_response(200, payload, out_headers)

    def _origin_ok(self, origin: str, own: str) -> bool:
        return (
            origin == own.rstrip("/")
            or "*" in self.allowed_origins
            or origin in self.allowed_origins
        )

    def _challenge(self, error: str | None = None) -> dict:
        parts = ['Bearer realm="scitex"']
        if self.resource_metadata_url:
            parts.append(f'resource_metadata="{self.resource_metadata_url}"')
        if error:
            parts.append(f'error="{error}"')
        return {"WWW-Authenticate": ", ".join(parts)}

    def _authenticate(self, request, hooks) -> ApiCaller:
        header = request.headers.get("authorization", "").strip()
        if not header:
            if self.anonymous:
                return anonymous_caller()
            raise ApiProblem(
                401,
                "api.unauthenticated",
                "send Authorization: Bearer <token>",
                headers=self._challenge(),
            )
        if hooks.authenticate is None:
            raise ApiProblem(
                503, "api.unavailable", "API authentication is not configured"
            )
        scheme, _, token = header.partition(" ")
        caller = None
        if scheme.lower() == "bearer" and token.strip():
            try:
                caller = hooks.authenticate(request.native)
            except Exception as exc:
                raise problem_from(exc) from exc
        if caller is None or caller.via == "session":
            # API-A002: a credential that is presented but does not resolve is
            # a 401, never a fall-back to anonymous or to the session.
            raise ApiProblem(
                401,
                "api.unauthenticated",
                "the bearer token is not valid",
                headers=self._challenge("invalid_token"),
            )
        return caller

    # ----------------------------------------------------------- JSON-RPC
    def _dispatch(self, method, params, rpc_id, caller, request, hooks, out_headers):
        if method == "initialize":
            asked = params.get("protocolVersion")
            result = {
                "protocolVersion": (
                    asked
                    if asked in SUPPORTED_PROTOCOL_VERSIONS
                    else SUPPORTED_PROTOCOL_VERSIONS[0]
                ),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.server_version,
                },
            }
            if self.instructions:
                result["instructions"] = self.instructions
            return result
        if method == "ping":
            return {}
        if method == "tools/list":
            return {
                "tools": [self.tool_json(s, caller) for s in self.tools_for(caller)]
            }
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or name not in self.specs:
                raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                raise RpcError(INVALID_PARAMS, "arguments must be an object")
            meta = params.get("_meta")
            result, call_id = call_hosted_tool(
                self.specs[name],
                self.tiers[name],
                arguments,
                caller,
                hooks=hooks,
                native=request.native,
                rpc_id=rpc_id,
                idempotency_key=(
                    meta.get("idempotency_key") if isinstance(meta, dict) else None
                ),
            )
            out_headers["X-Request-Id"] = call_id
            return result
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")


__all__ = ["HostedMcp"]
