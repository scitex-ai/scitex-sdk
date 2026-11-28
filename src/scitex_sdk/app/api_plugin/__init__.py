#!/usr/bin/env python3
"""The leaf API-plugin contract: what an approved leaf DECLARES about its API.

A leaf app (FigRecipe, Writer, Scholar, ...) owns the behaviour of its own
endpoints. What it does not own is the SHAPE a client may rely on: the routes,
the request/response/error schemas, the auth scope, the idempotency promise,
the pagination style, the rate/quota class, the audit level, the API version
and the deprecation window. Those cross a package boundary — browser, agent,
and thin native clients all read them — so they are DECLARED here as data and
checked at construction, not discovered by reading an implementation.

WHY A DECLARATION RATHER THAN THE IMPLEMENTATION. The operator's model
(2026-09-16): the public SDK lets clients be built against approved APIs, while
server-side leaf endpoint plugins are a HIGHER-TRUST class requiring SciTeX
approval. A contract that must be approved is a contract that must be readable
without executing the leaf: everything below is plain data, importable and
comparable, and the handler is named as a string, never imported here.

WHAT IS DELIBERATELY ABSENT. No Hub ORM, no middleware, no root-route
registration, no raw shell/path/argv, and no framework object: a route path is
a RELATIVE declaration that is validated (see :func:`_validate_path`) so it
cannot escape its mount, and the handler reference is an entry-point-style
``module:attr`` string. Nothing in this module serves a request — the host
composes routes; this layer says what may be composed.

FAIL CLOSED. Every rule below refuses at construction, because each one would
otherwise present as a working API: an undeclared auth scope opens an endpoint,
a mutating method with no idempotency declaration double-creates on retry, an
unstructured error leaves a client nothing to branch on, and a deprecation with
no sunset never arrives. Strictness is the feature; the alternative is a client
that ships against a promise nobody made.

ZERO THIRD-PARTY DEPENDENCIES. scitex-app's base install is stdlib plus
click/rich/scitex-config, and this module must stay importable from the CLI, the
MCP surface and a test process alike. The descriptors are therefore frozen
stdlib dataclasses, NOT pydantic models: the declaration layer is data, and
validation of a live REQUEST is the serving host's job. Flagged as a decision
for the card's owner — see the note in :data:`DESCRIPTOR_IMPLEMENTATION`.
"""

from __future__ import annotations

# The declaration layer is split into cohesive private modules; this package
# is the one public import path (``scitex_sdk.app.api_plugin``) and re-exports
# every public name callers already used.
from ._base import (
    API_ENTRY_POINT_GROUP,
    AUDIT_LEVELS,
    DESCRIPTOR_IMPLEMENTATION,
    FIELD_TYPES,
    HTTP_METHODS,
    IDEMPOTENCY_KEY_HEADER,
    MUTATING_METHODS,
    OAUTH2_FLOW,
    OAUTH_SECURITY_SCHEME,
    PAGINATION_STYLES,
    PROJECT_SCOPES,
    RECOMMENDED_COMPUTE_COSTS,
    RECOMMENDED_RATE_CLASSES,
    RESERVED_IDEMPOTENCY_HEADERS,
    TRANSPORTS,
    ApiPluginContractError,
)
from ._descriptors import (
    ApiError,
    ApiField,
    ApiSchema,
    Audit,
    AuthScope,
    Deprecation,
    Idempotency,
    Pagination,
    RateLimit,
)
from ._discovery import ApiPluginRef, discover_api_plugins
from ._plugin import ApiPlugin, OAuthProvider
from ._route import ApiRoute

# ``api_mount`` validates mount paths with the same rule as a declaration.
from ._validators import _validate_path as _validate_path

__all__ = [
    "API_ENTRY_POINT_GROUP",
    "AUDIT_LEVELS",
    "DESCRIPTOR_IMPLEMENTATION",
    "FIELD_TYPES",
    "HTTP_METHODS",
    "IDEMPOTENCY_KEY_HEADER",
    "MUTATING_METHODS",
    "OAUTH2_FLOW",
    "OAUTH_SECURITY_SCHEME",
    "PAGINATION_STYLES",
    "PROJECT_SCOPES",
    "RECOMMENDED_COMPUTE_COSTS",
    "RECOMMENDED_RATE_CLASSES",
    "RESERVED_IDEMPOTENCY_HEADERS",
    "TRANSPORTS",
    "ApiError",
    "ApiField",
    "ApiPlugin",
    "ApiPluginContractError",
    "ApiPluginRef",
    "ApiRoute",
    "ApiSchema",
    "Audit",
    "AuthScope",
    "Deprecation",
    "Idempotency",
    "OAuthProvider",
    "Pagination",
    "RateLimit",
    "discover_api_plugins",
]

# EOF
