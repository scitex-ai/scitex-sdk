#!/usr/bin/env python3
"""OpenAPI fragment renderers for declared schemas and the OAuth scheme."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._base import OAUTH2_FLOW
from ._descriptors import ApiSchema

if TYPE_CHECKING:
    from ._plugin import OAuthProvider


def _media_type(transport: str) -> str:
    """The OpenAPI media type for a declared transport."""
    return {
        "json": "application/json",
        "sse": "text/event-stream",
        "binary": "application/octet-stream",
    }[transport]


def _security_scheme_fragment(provider: OAuthProvider) -> dict[str, Any]:
    """The ``components.securitySchemes`` entry for :data:`OAUTH_SECURITY_SCHEME`.

    The scheme an OAuth2 requirement is written against is an ``oauth2``
    scheme, and its ``flows`` are the endpoints that actually issue the token:
    the requirement's value is an array of SCOPES, so the scheme must publish a
    scope map and the flow that grants them. An ``http``/``bearer`` scheme
    carrying an OAuth2 scope array is a document that describes neither — it
    tells a consumer scopes exist while declaring no way to obtain them — so
    this renderer emits only the honest form, using the endpoints the plugin
    DECLARED (nothing here invents a URL).

    A fresh dict per call: the fragment is handed to a host that merges it, and
    a shared module-level object would let one merge mutate every later one.
    """
    return {
        "type": "oauth2",
        "description": (
            "SciTeX OAuth2 (authorization code + PKCE). Run the flow against "
            "the declared provider and present the issued access token as a "
            "bearer credential. The scopes below are the ones this API's "
            "operation requirements name."
        ),
        "flows": {
            OAUTH2_FLOW: {
                "authorizationUrl": provider.authorization_url,
                "tokenUrl": provider.token_url,
                "scopes": dict(provider.scopes),
            }
        },
    }


def _schema_fragment(schema: ApiSchema) -> dict[str, Any]:
    """A JSON-Schema object for a declared ``ApiSchema``.

    Closed with ``additionalProperties: false``: the declared fields ARE the
    body, so a consumer can rely on the shape instead of accepting whatever a
    client (or a mistyped field name) sends alongside it.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []
    for item in schema.fields:
        entry: dict[str, Any] = {"type": item.type}
        if item.description:
            entry["description"] = item.description
        if item.enum:
            entry["enum"] = list(item.enum)
        properties[item.name] = entry
        if item.required:
            required.append(item.name)
    fragment: dict[str, Any] = {
        "title": schema.name,
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        fragment["required"] = required
    return fragment

# EOF
