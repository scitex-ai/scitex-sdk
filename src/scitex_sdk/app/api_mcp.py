#!/usr/bin/env python3
"""MCP tools generated from declared operations: REST and MCP map 1:1.

Every operation of an :class:`~.api_plugin.ApiPlugin` becomes one tool named
``<package>_<resource>_<verb>`` (see :mod:`.api_ops`). The tool's input schema
IS the operation's request schema (plus the item id for item operations),
and calling it runs :func:`.api_exec.execute` — the same scope check,
validation, handler and envelope as the REST endpoint. A leaf therefore
writes no MCP tool by hand; it registers its plugin::

    from scitex_sdk.app.api_mcp import register_fastmcp
    register_fastmcp(mcp, PLUGIN)

Local MCP (stdio) acts for the local user: scope ``*``, and a project-scoped
operation's ``project`` is a LOCAL project directory. A remote MCP host passes
its own ``caller`` and ``resolve_project`` (the token's scopes, the host's
project authorization), exactly as the REST adapter does.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .api_exec import ApiCaller, ApiProblem, execute
from .api_ops import ApiOperation, operations

_PY_TYPES = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


@dataclass(frozen=True)
class McpToolSpec:
    """One generated tool: its name, description, JSON schemas, operation.

    ``output_schema`` describes the tool's ``structuredContent`` — the REST
    body — or is ``None`` when the operation declares no body shape.
    ``annotations`` are the MCP behaviour hints derived from the verb.
    """

    name: str
    description: str
    input_schema: dict
    operation: ApiOperation
    output_schema: dict | None = None
    title: str = ""
    annotations: dict | None = None


def _property(f) -> dict:
    prop = {"type": f.type}
    if f.description:
        prop["description"] = f.description
    if f.enum:
        prop["enum"] = list(f.enum)
    return prop


def _body_schema(schema) -> dict:
    """A declared response schema as JSON Schema, typed but OPEN.

    Field types and descriptions are the declaration; the object is left
    open (no ``required``, extra keys allowed) because an MCP client
    validates ``structuredContent`` strictly, and a leaf that returns one
    field more than it documented must not turn a working REST call into a
    failed tool call. The envelope keys around it are exact.
    """
    return {
        "type": "object",
        "title": schema.name,
        "properties": {f.name: _property(f) for f in schema.fields},
    }


def output_schema(op: ApiOperation) -> dict | None:
    """JSON Schema of the REST body an operation answers (its MCP output)."""
    if op.is_async:
        return {
            "type": "object",
            "properties": {"job": _body_schema(op.response)},
            "required": ["job"],
        }
    item = _body_schema(op.response) if op.response is not None else {}
    if op.paginated:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": item},
                "has_more": {"type": "boolean"},
                "next_cursor": {"type": ["string", "null"]},
                "total": {"type": "integer"},
            },
            "required": ["data", "has_more", "next_cursor"],
        }
    if op.response is None:
        return None
    return {
        "type": "object",
        "properties": {"data": item},
        "required": ["data"],
    }


def _annotations(op: ApiOperation) -> dict:
    read = op.access == "read"
    return {
        "title": op.summary or op.operation_id,
        "readOnlyHint": read,
        "destructiveHint": op.verb == "delete",
        "idempotentHint": read or op.verb in ("update", "delete"),
        "openWorldHint": False,
    }


def _fields(op: ApiOperation) -> list:
    from .api_plugin import ApiField

    fields = []
    if op.id_param:
        fields.append(
            ApiField(op.id_param, "string", True, f"Id of the {op.resource[:-1]}")
        )
    fields.extend(op.request_fields())
    return fields


def tool_specs(plugin) -> list:
    """The MCP tool of every operation of ``plugin``."""
    specs = []
    for op in operations(plugin):
        properties = {}
        required = []
        for f in _fields(op):
            properties[f.name] = _property(f)
            if f.required:
                required.append(f.name)
        access = "public, no credential needed" if op.public else f"scope {op.scope}"
        description = (
            f"{op.summary or op.operation_id} (REST {op.method} {op.url}; {access})"
        ).strip()
        if op.is_async:
            description += " Answers a job; poll it until it finishes."
        specs.append(
            McpToolSpec(
                name=op.mcp_name,
                description=description,
                input_schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
                operation=op,
                output_schema=output_schema(op),
                title=op.summary or op.operation_id,
                annotations=_annotations(op),
            )
        )
    return specs


def local_caller() -> ApiCaller:
    """The local stdio user: every scope over their own machine."""
    import getpass

    class _Local:
        is_authenticated = True
        username = getpass.getuser()
        pk = username

    return ApiCaller(user=_Local(), scopes=("*",), via="local")


def local_project(caller, project_id: str, write: bool):
    """A local project directory as the host's ProjectAccess."""
    from scitex_sdk.host import AccessError, ProjectAccess

    root = Path(project_id).expanduser()
    if not root.is_dir():
        raise AccessError("Project not available", 404)
    return ProjectAccess(str(root), root.name, root.resolve(), can_write=True)


def call_tool(
    spec: McpToolSpec,
    arguments: dict,
    *,
    caller: ApiCaller | None = None,
    resolve_project: Callable | None = None,
) -> dict:
    """Run one tool; the REST body on success, :class:`ApiProblem` otherwise."""
    op = spec.operation
    args = dict(arguments)
    item_id = args.pop(op.id_param, None) if op.id_param else None
    result = execute(
        op,
        caller or local_caller(),
        args,
        item_id=item_id,
        resolve_project=resolve_project or local_project,
    )
    if result.status >= 400:
        body = result.body or {}
        raise ApiProblem(
            result.status, body.get("code", "api.error"), body.get("detail", "")
        )
    return result.body if result.body is not None else {"status": result.status}


def _tool_function(spec: McpToolSpec, caller, resolve_project) -> Callable:
    params = []
    annotations = {}
    for f in _fields(spec.operation):
        kind = _PY_TYPES[f.type]
        annotation = kind if f.required else Optional[kind]
        params.append(
            inspect.Parameter(
                f.name,
                inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty if f.required else None,
                annotation=annotation,
            )
        )
        annotations[f.name] = annotation

    def tool(**kwargs):
        arguments = {k: v for k, v in kwargs.items() if v is not None}
        try:
            return call_tool(
                spec, arguments, caller=caller, resolve_project=resolve_project
            )
        except ApiProblem as problem:
            try:
                from fastmcp.exceptions import ToolError
            except ImportError:  # pragma: no cover - fastmcp is the host here
                raise RuntimeError(problem.detail) from problem
            raise ToolError(
                json.dumps(
                    {
                        "status": problem.status,
                        "code": problem.code,
                        "detail": problem.detail,
                    }
                )
            ) from problem

    tool.__name__ = spec.name
    tool.__doc__ = spec.description
    tool.__signature__ = inspect.Signature(params, return_annotation=dict)
    tool.__annotations__ = {**annotations, "return": dict}
    return tool


def register_fastmcp(mcp, plugin, *, caller=None, resolve_project=None) -> list:
    """Register every operation of ``plugin`` as a tool of a FastMCP server."""
    names = []
    for spec in tool_specs(plugin):
        fn = _tool_function(spec, caller, resolve_project)
        mcp.tool(name=spec.name, description=spec.description)(fn)
        names.append(spec.name)
    return names


__all__ = [
    "McpToolSpec",
    "call_tool",
    "local_caller",
    "local_project",
    "output_schema",
    "register_fastmcp",
    "tool_specs",
]
