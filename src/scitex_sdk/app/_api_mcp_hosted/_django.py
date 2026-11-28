#!/usr/bin/env python3
"""Mount hosted MCP in a Django host, with the hooks REST serving uses.

A host adds ONE pattern, before the ``api/v1/`` catch-all::

    from scitex_sdk.app.api_mcp_http import mcp_urlpattern
    urlpatterns += [mcp_urlpattern()] + api_urlpatterns()

Settings (all optional except the caller, as for REST):

``SCITEX_API_CALLER``                    the authenticator (shared with REST)
``SCITEX_API_RATE_LIMITER`` / ``SCITEX_API_METER`` / ``SCITEX_API_IDEMPOTENCY_STORE``
``SCITEX_API_MCP_TOOL_TIERS``            ``{tool name or operation id: tier}``
``SCITEX_API_MCP_ANONYMOUS``             let credential-less callers see public tools
``SCITEX_API_MCP_RESOURCE_METADATA_URL`` RFC 9728 URL named in the 401 challenge
``SCITEX_API_MCP_ALLOWED_ORIGINS``       extra ``Origin`` values allowed
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ..api_mcp import tool_specs
from ._endpoint import HostedMcp
from ._wire import McpHooks, McpHttpRequest

MCP_ROUTE = "api/v1/mcp"


def settings_hooks() -> McpHooks:
    """The REST hooks of the Django settings, read now (once per request)."""
    from ..api_serve import _hook, _project_resolver

    return McpHooks(
        authenticate=_hook("SCITEX_API_CALLER"),
        project_resolver=_project_resolver,
        rate_limiter=_hook("SCITEX_API_RATE_LIMITER"),
        meter=_hook("SCITEX_API_METER"),
        idempotency_store=_hook("SCITEX_API_IDEMPOTENCY_STORE"),
    )


def endpoint_from_settings(refs=None) -> HostedMcp:
    """A :class:`HostedMcp` over the host's admitted plugins and settings."""
    from django.conf import settings

    from ..api_serve import admitted_plugins

    return HostedMcp(
        [plugin for _ref, plugin in admitted_plugins(refs)],
        tool_tiers=getattr(settings, "SCITEX_API_MCP_TOOL_TIERS", None),
        anonymous=bool(getattr(settings, "SCITEX_API_MCP_ANONYMOUS", False)),
        resource_metadata_url=getattr(
            settings, "SCITEX_API_MCP_RESOURCE_METADATA_URL", None
        ),
        allowed_origins=tuple(
            getattr(settings, "SCITEX_API_MCP_ALLOWED_ORIGINS", ()) or ()
        ),
    )


def mcp_view(endpoint: HostedMcp | None = None, *, refs=None, hooks=None):
    """The Django view of the MCP endpoint.

    ``endpoint`` defaults to :func:`endpoint_from_settings`, built on the
    first request; ``hooks`` default to :func:`settings_hooks`, read on
    every request.
    """
    from django.http import HttpResponse
    from django.views.decorators.csrf import csrf_exempt

    built: list = [endpoint] if endpoint is not None else []

    @csrf_exempt
    def view(request):
        if not built:
            built.append(endpoint_from_settings(refs))
        answer = built[0].handle(
            McpHttpRequest(
                method=request.method,
                headers={k.lower(): v for k, v in request.headers.items()},
                body=request.body,
                native=request,
                origin=f"{request.scheme}://{request.get_host()}",
            ),
            hooks or settings_hooks(),
        )
        response = HttpResponse(answer.body, status=answer.status)
        if "Content-Type" not in answer.headers:
            del response["Content-Type"]
        for key, value in answer.headers.items():
            response[key] = value
        return response

    view.__name__ = "api_mcp"
    return view


def mcp_urlpattern(route: str = MCP_ROUTE, **kwargs):
    """``path(route, mcp_view(**kwargs))``; list it before the catch-all."""
    from django.urls import path

    return path(route, mcp_view(**kwargs), name="api-mcp")


def protected_resource_metadata(
    resource: str,
    authorization_servers: Sequence[str],
    plugins: Iterable = (),
    *,
    documentation: str | None = None,
) -> dict:
    """The RFC 9728 protected-resource metadata of the MCP endpoint.

    ``resource`` is the endpoint's canonical URI
    (``https://scitex.ai/api/v1/mcp``); ``scopes_supported`` are the derived
    scopes of ``plugins``. The host serves it at
    ``/.well-known/oauth-protected-resource/api/v1/mcp``.
    """
    scopes = sorted(
        {
            spec.operation.scope
            for plugin in plugins
            for spec in tool_specs(plugin)
            if not spec.operation.public
        }
    )
    doc = {
        "resource": resource,
        "authorization_servers": list(authorization_servers),
        "scopes_supported": scopes,
        "bearer_methods_supported": ["header"],
    }
    if documentation:
        doc["resource_documentation"] = documentation
    return doc


__all__ = [
    "MCP_ROUTE",
    "endpoint_from_settings",
    "mcp_urlpattern",
    "mcp_view",
    "protected_resource_metadata",
    "settings_hooks",
]
