#!/usr/bin/env python3
"""One hosted ``tools/call``: the REST execution core, an MCP result shape.

Success (API-M004): ``structuredContent`` is the REST body (``{data}`` /
``{data, has_more, next_cursor}`` / ``{job}``), the same JSON is the text
content, ``_meta`` carries ``request_id`` and ``operation_id``.

Failure (API-M003): ``isError: true`` and ``structuredContent`` is the full
RFC 9457 problem (``type, title, status, detail, code, request_id,
retryable, errors``), the same body REST answers with problem+json.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping
from typing import Any

from ..api_exec import ApiCaller, ApiProblem, execute, params_digest, problem_from
from ..api_tier import (
    TieredCall,
    anonymous_allowed,
    anonymous_caller,
    decide,
    run_tiered,
)
from ._policy import denial
from ._wire import McpHooks


def call_hosted_tool(
    spec,
    tier: str,
    arguments: Mapping[str, Any],
    caller: ApiCaller,
    *,
    hooks: McpHooks,
    native: Any = None,
    rpc_id: Any = None,
    idempotency_key: str | None = None,
) -> tuple[dict, str]:
    """``(CallToolResult, request_id)`` of one tool call for ``caller``."""
    op = spec.operation
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    replayed = False
    if caller.via == "anonymous" and not op.public and anonymous_allowed(op)[0]:
        # The per-operation anonymous caller of the public tier: this
        # operation's scope only, keyed by client IP (contract §12.3).
        caller = anonymous_caller(op, native)
    tiered = TieredCall(decide(op, caller, native))
    try:
        status, body, replayed = _run(
            spec,
            tier,
            dict(arguments),
            caller,
            hooks,
            native,
            request_id,
            idempotency_key,
            tiered,
        )
    except Exception as exc:  # noqa: BLE001 - the one problem boundary
        problem = problem_from(exc)
        status, body = problem.status, problem.body(request_id)
    if body is None:  # 204: nothing to say beyond success
        body = {"data": None}
    meta = {
        "request_id": request_id,
        "operation_id": op.operation_id,
        "status": status,
        "priority_class": tiered.decision.priority_class,
    }
    if replayed:
        meta["idempotent_replayed"] = True
    text = json.dumps(body, default=str)
    if hooks.meter is not None:
        egress = len(text.encode())
        hooks.meter.record(
            {
                "request_id": request_id,
                "operation_id": op.operation_id,
                "package": op.package,
                "status": status,
                "duration_seconds": round(time.monotonic() - started, 6),
                "egress_bytes": egress,
                "caller": caller.identity,
                "token_id": caller.token_id,
                "user_id": getattr(caller.user, "pk", None),
                "transport": "mcp",
                "jsonrpc_id": rpc_id,
                **tiered.meter_fields(egress),
            }
        )
    result = {
        "content": [{"type": "text", "text": text}],
        "structuredContent": body,
        "isError": status >= 400,
        "_meta": meta,
    }
    return result, request_id


def _run(
    spec, tier, args, caller, hooks, native, request_id, idempotency_key, tiered
):
    """``(status, body, replayed)``; raises for a refusal before execution."""
    op = spec.operation
    refused = denial(caller, spec, tier)
    if refused is not None:
        raise refused
    if op.project_scoped and caller.project and not args.get("project"):
        # A project token's calls default to its own project.
        args["project"] = caller.project
    if hooks.rate_limiter is not None:
        hooks.rate_limiter.check(caller, op, native)
    item_id = args.pop(op.id_param, None) if op.id_param else None
    store = hooks.idempotency_store if op.access == "write" else None
    idem = digest = None
    if store is not None and idempotency_key:
        # Only a key the client chose (`_meta.idempotency_key`): JSON-RPC ids
        # restart at 0 in every client session, so an id cannot tell a retry
        # from a new call.
        idem = (caller.identity, op.operation_id, f"mcp:{idempotency_key}")
        digest = params_digest({"params": args, "id": item_id})
        previous = store.get(idem)
        if previous is not None:
            if previous[0] != digest:
                raise ApiProblem(
                    409,
                    "api.idempotency_mismatch",
                    "this idempotency_key was used with other arguments",
                )
            return previous[1], previous[2], True
    resolver = (
        hooks.project_resolver(native) if hooks.project_resolver is not None else None
    )
    body_bytes = len(json.dumps(args, default=str).encode())
    result, _ = run_tiered(
        op,
        caller,
        native,
        lambda decision: execute(
            op,
            caller,
            args,
            item_id=item_id,
            resolve_project=resolver,
            request=native,
            request_id=request_id,
            tier=decision,
        ),
        request_bytes=body_bytes,
        tiered=tiered,
    )
    if idem is not None and result.status < 500:
        store.put(idem, digest, result.status, result.body)
    return result.status, result.body, False


__all__ = ["call_hosted_tool"]
