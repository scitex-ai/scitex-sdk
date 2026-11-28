#!/usr/bin/env python3
"""Hosted MCP: declared operations served over MCP Streamable HTTP.

An external agent that knows a URL and a key connects to the host's MCP
endpoint (``/api/v1/mcp`` on the Hub) and uses the tools its key grants.
Hosted MCP is the REST contract on another transport, not a second API:

- the tools are exactly :func:`.api_mcp.tool_specs` of the admitted plugins
  (API-M001), named ``<package>_<resource>_<verb>``, with the input and
  output JSON Schemas derived from the operation;
- every ``tools/call`` runs :func:`.api_exec.execute`, the function REST
  runs, so scopes, validation, project authorization, handlers and result
  shapes are identical;
- ``tools/list`` shows only the tools the caller's scopes and tier reach
  (API-M002);
- authentication failures are HTTP 401 with ``WWW-Authenticate``; tool
  failures are ``isError`` results whose ``structuredContent`` is the full
  problem object with ``request_id`` (API-M003); a success carries the REST
  body and ``_meta.request_id`` (API-M004).

AUTHENTICATION is pluggable: an authenticator is
``authenticate(request) -> ApiCaller | None``, the same contract as the REST
``SCITEX_API_CALLER`` hook, so a host plugs its token model in without new
code. Only ``Authorization: Bearer`` is accepted (API-A001); a session
caller is refused, since a browser cookie must not drive tools.

Django host (one line, before the ``api/v1/`` catch-all)::

    from scitex_sdk.app.api_mcp_http import mcp_urlpattern
    urlpatterns += [mcp_urlpattern()] + api_urlpatterns()

Any other host builds :class:`HostedMcp` and passes
:class:`McpHttpRequest` values to :meth:`HostedMcp.handle`.
"""

from __future__ import annotations

from ._api_mcp_hosted._django import (
    MCP_ROUTE,
    endpoint_from_settings,
    mcp_urlpattern,
    mcp_view,
    protected_resource_metadata,
    settings_hooks,
)
from ._api_mcp_hosted._endpoint import HostedMcp
from ._api_mcp_hosted._policy import TIERS, anonymous_caller, tier_rank
from ._api_mcp_hosted._wire import (
    SUPPORTED_PROTOCOL_VERSIONS,
    McpHooks,
    McpHttpRequest,
    McpHttpResponse,
)

__all__ = [
    "MCP_ROUTE",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "TIERS",
    "HostedMcp",
    "McpHooks",
    "McpHttpRequest",
    "McpHttpResponse",
    "anonymous_caller",
    "endpoint_from_settings",
    "mcp_urlpattern",
    "mcp_view",
    "protected_resource_metadata",
    "settings_hooks",
    "tier_rank",
]
