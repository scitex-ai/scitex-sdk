#!/usr/bin/env python3
"""The OAuth provider and the whole-plugin declaration (ApiPlugin)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ._base import OAUTH_SECURITY_SCHEME, ApiPluginContractError
from ._openapi import _media_type, _schema_fragment, _security_scheme_fragment
from ._route import (
    ApiRoute,
    _canonical_path,
    _declared_schemas,
    _encode_operation_id,
    _operation_claims,
)
from ._validators import (
    _require_component_name,
    _require_elements,
    _require_oauth_endpoint_url,
    _require_text,
    _require_version,
)


@dataclass(frozen=True)
class OAuthProvider:
    """The OAuth2 authorization server a plugin's scopes are ISSUED by.

    Required to be declared whenever a route declares OAuth scopes, because an
    OAuth2 scheme IS its flows: the fragment's ``security`` requirement carries
    a scope array, and a scheme with no ``flows``/``scopes`` would name scopes
    the document never defines. The endpoints are DECLARED data — the fragment
    never invents a URL, because a generated production URL is a promise the
    leaf never made and the deployment may not honour.

    ``authorization_url``/``token_url`` must be absolute ``http(s)`` URLs (a
    localhost deployment is legitimate, a bare host or a relative path is not:
    a client has to be able to construct the request). Each is validated as a
    WHOLE RFC 3986 URI against the RAW declared string — no control character,
    no whitespace (padding included), no fragment (RFC 6749 §3.1), no userinfo,
    a host the authority grammar accepts, and a parse that agrees with the text
    it was handed — because the raw string is what gets stored and emitted.
    ``scopes`` is the map the emitted scheme publishes, scope name -> human
    description; every scope a route requires must appear in it (checked by
    :class:`ApiPlugin`).
    """

    authorization_url: str
    token_url: str
    scopes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # STORED, not merely checked: these URLs are emitted inside the OAuth2
        # flow (authorizationUrl / tokenUrl), so the string that is validated
        # has to be the string that is stored. The validation reads the RAW
        # declaration rather than the parser's normalized result, because
        # urlsplit deletes the controls and spaces it parses — a padded URL
        # used to pass a check written against `parts` and then reach the
        # document unchanged, and an embedded newline (invisible to the parse)
        # was emitted verbatim. Now a URL that is not a complete RFC 3986 URI
        # is refused instead of normalized.
        for label, url in (
            ("authorization_url", self.authorization_url),
            ("token_url", self.token_url),
        ):
            object.__setattr__(self, label, _require_oauth_endpoint_url(url, label))
        if not isinstance(self.scopes, Mapping):
            raise ApiPluginContractError(
                "OAuth scopes must be a mapping of scope name to description "
                f"(got {self.scopes!r}, a {type(self.scopes).__name__}); the "
                "scheme's scope map is what gives an operation requirement's "
                "scope its meaning"
            )
        if not self.scopes:
            raise ApiPluginContractError(
                "OAuth scopes declares none; a scheme whose scope map is empty "
                "defines no scope any requirement may name"
            )
        # The map is stored in validated form too: each name and description
        # stripped, and two spellings of ONE scope refused rather than kept as
        # two keys (a requirement would then resolve to whichever key survived).
        normalized: dict[str, str] = {}
        for name, description in self.scopes.items():
            scope = _require_text(name, "OAuth scope name")
            if scope in normalized:
                raise ApiPluginContractError(
                    f"OAuth scopes declares {scope!r} twice ({name!r} and "
                    "another spelling of the same name); the scheme's scope map "
                    "is keyed by name, so one of the two would be dropped and a "
                    "requirement naming it would resolve to nothing"
                )
            normalized[scope] = _require_text(
                description, f"description of OAuth scope {name!r}"
            )
        object.__setattr__(self, "scopes", normalized)


@dataclass(frozen=True)
class ApiPlugin:
    """One leaf's whole API declaration, published under an entry point.

    ``oauth`` is the authorization server its scopes are issued by. It is
    optional only for a plugin that declares NO scopes anywhere: the moment one
    route declares a scope, construction refuses a missing (or non-covering)
    provider, so a scoped API cannot be published without saying which server
    issues its scopes.
    """

    id: str
    title: str
    api_version: str
    routes: Sequence[ApiRoute] = field(default_factory=tuple)
    oauth: OAuthProvider | None = None

    def __post_init__(self) -> None:
        # Stored in validated form: the id prefixes every operationId and names
        # the plugin in every refusal, the version is emitted as
        # x-scitex-api-version, and the title reaches the document's `info`.
        object.__setattr__(
            self, "id", _require_component_name(self.id, "plugin id")
        )
        object.__setattr__(self, "title", _require_text(self.title, "plugin title"))
        object.__setattr__(
            self, "api_version", _require_version(self.api_version, "api_version")
        )
        object.__setattr__(self, "routes", _require_elements(
            self.routes, ApiRoute, f"routes of api plugin {self.id!r}"
        ))
        if self.oauth is not None and not isinstance(self.oauth, OAuthProvider):
            raise ApiPluginContractError(
                f"oauth of api plugin {self.id!r} is {self.oauth!r}, a "
                f"{type(self.oauth).__name__}; expected an instance of "
                "OAuthProvider or None"
            )
        if not self.routes:
            raise ApiPluginContractError(
                f"api plugin {self.id!r} declares no routes; an empty plugin "
                "cannot be distinguished from one that failed to load"
            )
        self._refuse_duplicate_route_keys()
        self._refuse_duplicate_schema_names()
        self._refuse_uncovered_oauth_scopes()

    def _refuse_duplicate_route_keys(self) -> None:
        """Refuse two routes claiming the same canonical path AND method.

        The host can compose only one operation per path and method, so the
        loser would be dropped silently — an endpoint the leaf believes it
        published and no client can reach. The comparison is on the CANONICAL
        path (see :func:`_canonical_path`), so two same-hierarchy templates
        (``things/{id}`` and ``things/{name}``, which OpenAPI keys as ONE path)
        cannot slip past as "different" routes.

        DISJOINT methods on one canonical path are NOT a collision and are not
        refused here: ``GET x`` and ``POST x`` are two operations on one URL, and
        the renderer merges them into one Path Item. The whole rule lives in
        :func:`_operation_claims`, which the renderer calls too, so construction
        and rendering cannot disagree about what a duplicate is.
        """
        _operation_claims(self.routes, self.id)

    def _refuse_uncovered_oauth_scopes(self) -> None:
        """Every scope a route requires must be a scope the provider declares.

        The emitted scheme is an OAuth2 ``authorizationCode`` flow, whose
        ``scopes`` map is where a scope name gets its meaning. An operation
        requirement naming a scope that map does not carry is a security
        statement no client can resolve, and the flow that would issue it is
        undescribed. A plugin with scoped routes and NO provider at all is
        refused for the same reason: the honest scheme for a scope-carrying
        requirement needs the authorization and token endpoints, and this layer
        will not invent production URLs.
        """
        used: list[str] = []
        for route in self.routes:
            used.extend(route.auth.scopes)
        if not used:
            return
        if self.oauth is None:
            raise ApiPluginContractError(
                f"api plugin {self.id!r} declares scopes {tuple(used)} on its "
                "routes but no OAuth provider; a scope-carrying security "
                "requirement is satisfied by an oauth2 scheme, whose flows must "
                "name the authorization and token endpoints. Declare "
                "OAuthProvider(authorization_url=..., token_url=..., scopes=..."
                ")."
            )
        missing = [scope for scope in used if scope not in self.oauth.scopes]
        if missing:
            raise ApiPluginContractError(
                f"api plugin {self.id!r} requires scope(s) {tuple(missing)} that "
                f"its OAuth provider does not declare (declared: "
                f"{tuple(self.oauth.scopes)}); an operation requirement naming a "
                "scope the scheme's map omits resolves to nothing"
            )

    def _refuse_duplicate_schema_names(self) -> None:
        """One flat component namespace: a name may describe only one thing.

        OpenAPI keys components by NAME, so two schemas sharing one would
        silently overwrite each other and the survivor would ship the other's
        shape. A schema's name and another schema's FIELD name are read from the
        same flat namespace by a generator, so that collision is refused by this
        same rule rather than by a weaker second one. Two schemas sharing a
        field NAME is not a collision — fields are nested under their schema —
        and stays legal.
        """
        schema_names: dict[str, str] = {}
        field_names: dict[str, str] = {}
        for route in self.routes:
            for role, schema in _declared_schemas(route):
                owner = f"{role} schema of route {route.path!r}"
                if schema.name in schema_names:
                    raise ApiPluginContractError(
                        f"api plugin {self.id!r} declares schema name "
                        f"{schema.name!r} twice ({schema_names[schema.name]} and "
                        f"{owner}); components are keyed by name, so one of the "
                        "two would silently overwrite the other"
                    )
                if schema.name in field_names:
                    raise ApiPluginContractError(
                        f"api plugin {self.id!r} names {owner} "
                        f"{schema.name!r}, which is already a declared FIELD "
                        f"({field_names[schema.name]}); a name is one thing in "
                        "this namespace, not a schema here and a field there"
                    )
                for item in schema.fields:
                    if item.name in schema_names:
                        raise ApiPluginContractError(
                            f"api plugin {self.id!r} declares field "
                            f"{item.name!r} on {owner}, which is already the "
                            f"NAME of {schema_names[item.name]}; a name is one "
                            "thing in this namespace, not a schema here and a "
                            "field there"
                        )
                    field_names.setdefault(item.name, owner)
                schema_names[schema.name] = owner

    def openapi_fragment(self) -> dict[str, Any]:
        """An OpenAPI 3.1 fragment a host can merge into its own document.

        This is a VALID document, not an approximation of one: paths are keyed
        by the absolute path the host will serve (the declaration is relative to
        the mount, the document is not), every declared ``{param}`` is emitted
        as an ``in: path`` parameter, each operation is built for its OWN method
        (so operationIds are unique and the metadata is method-specific), a
        scoped route carries a standard ``security`` requirement naming
        :data:`OAUTH_SECURITY_SCHEME` — an OAuth2 scheme whose ``flows`` are the
        provider the plugin DECLARED — and every generated schema closes itself
        with ``additionalProperties: false``.

        Two document-level invariants are re-checked here even though
        construction already enforces them, because this is the function that
        would otherwise ship an invalid document: no two operations share an
        ``operationId``, and no two routes claim one canonical path with the same
        method. Both raise :class:`ApiPluginContractError` rather than returning
        a document a validator would reject with no author left to point at —
        and both go through :func:`_operation_claims`, the same rule
        construction applies, so the two layers agree on what a duplicate is.
        DISJOINT methods on one canonical path are not a duplicate: ``GET x`` and
        ``POST x``, declared as two routes, merge into ONE ``/x`` Path Item
        carrying both operations (each built for its own method), which is what
        the public model already accepts.

        Declared metadata OpenAPI has no field for (idempotency, rate/quota
        class, audit level, project scope, transport, compute cost) rides in
        ``x-scitex-*`` extensions, which is where a specification-compliant
        consumer ignores them rather than rejects the document.
        """
        paths: dict[str, Any] = {}
        schemas: dict[str, Any] = {}
        operation_ids: dict[str, str] = {}
        # `spellings` maps a canonical path to the ONE OpenAPI path key its
        # routes emit, which is what makes the merge a merge: two routes with
        # disjoint methods share the key, so `setdefault` hands them the SAME
        # Path Item and each operation lands in its own method slot.
        _claims, spellings = _operation_claims(self.routes, self.id)
        for route in self.routes:
            entry = paths.setdefault(f"/{spellings[_canonical_path(route.path)]}", {})
            for method in route.methods:
                operation = self._operation(route, method, schemas)
                operation_id = operation["operationId"]
                if operation_id in operation_ids:
                    raise ApiPluginContractError(
                        f"api plugin {self.id!r} generated operationId "
                        f"{operation_id!r} for both {operation_ids[operation_id]} "
                        f"and {method} /{route.path}; OpenAPI requires "
                        "operationIds to be unique across the whole document, so "
                        "the id is refused here rather than emitted as a document "
                        "no validator will accept"
                    )
                operation_ids[operation_id] = f"{method} /{route.path}"
                entry[method.lower()] = operation
        security_schemes: dict[str, Any] = {}
        if self.oauth is not None:
            security_schemes[OAUTH_SECURITY_SCHEME] = _security_scheme_fragment(self.oauth)
        return {
            "paths": paths,
            "components": {
                "schemas": schemas,
                "securitySchemes": security_schemes,
            },
        }

    def _operation(
        self, route: ApiRoute, method: str, schemas: dict[str, Any]
    ) -> dict[str, Any]:
        """The operation for ONE ``(route, method)`` pair.

        Built per method rather than deep-copied: one shared dict would give a
        GET and a POST the same ``operationId`` (which OpenAPI forbids) and let
        one method's ``parameters`` stand in for the other's.
        """
        operation: dict[str, Any] = {
            "operationId": self._operation_id(route, method),
            "x-scitex-transport": route.transport,
            "x-scitex-project-scope": route.auth.project_scope,
            "x-scitex-audit": route.audit.level,
            "x-scitex-rate-class": route.rate.rate_class,
            "x-scitex-compute-cost": route.rate.compute_cost,
            "x-scitex-api-version": self.api_version,
        }
        if route.summary:
            operation["summary"] = route.summary
        if route.path_params:
            operation["parameters"] = [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
                for name in route.path_params
            ]
        if route.auth.public:
            operation["security"] = []
        elif route.auth.scopes:
            operation["security"] = [{OAUTH_SECURITY_SCHEME: list(route.auth.scopes)}]
            operation["x-scitex-oauth-scopes"] = list(route.auth.scopes)
        if route.auth.session:
            operation["x-scitex-session"] = True
        if route.read_only:
            operation["x-scitex-read-only"] = True
        if route.idempotency.required:
            operation["x-scitex-idempotency-key-header"] = route.idempotency.key_header
        if route.pagination.style != "none":
            operation["x-scitex-pagination"] = {
                "style": route.pagination.style,
                "default_limit": route.pagination.default_limit,
                "max_limit": route.pagination.max_limit,
            }
        if route.deprecation is not None:
            operation["deprecated"] = True
            operation["x-scitex-sunset-version"] = route.deprecation.sunset_version
            if route.deprecation.replacement:
                operation["x-scitex-replacement"] = route.deprecation.replacement
        if route.handler:
            operation["x-scitex-handler"] = route.handler
        if route.response is not None:
            schemas[route.response.name] = _schema_fragment(route.response)
            operation["responses"] = {
                "200": {
                    "description": route.response.name,
                    "content": {
                        _media_type(route.transport): {
                            "schema": {"$ref": f"#/components/schemas/{route.response.name}"}
                        }
                    },
                }
            }
        if route.errors:
            operation.setdefault("responses", {})["default"] = {
                "description": "declared errors",
                "x-scitex-errors": [
                    {
                        "code": error.code,
                        "status": error.status,
                        "message": error.message,
                        "retryable": error.retryable,
                    }
                    for error in route.errors
                ],
            }
        if route.request is not None:
            schemas[route.request.name] = _schema_fragment(route.request)
            operation["requestBody"] = {
                "content": {
                    _media_type(route.transport): {
                        "schema": {"$ref": f"#/components/schemas/{route.request.name}"}
                    }
                }
            }
        return operation

    def _operation_id(self, route: ApiRoute, method: str) -> str:
        """A document-unique ``operationId`` that NAMES its method and its path.

        OpenAPI requires operationIds to be unique across the whole document, so
        the lowercased method is part of the id: without it, a route declaring
        both GET and POST would publish two operations under one id.

        The id must be INJECTIVE in ``(plugin id, method, path)``. A lossy
        ``path.replace("/", "_")`` was not: ``a/b_c`` and ``a_b/c`` both became
        ``a_b_c``, and the validator refused the resulting document with
        ``DuplicateOperationIDError``. Both the id and the path are therefore
        percent-encoded (see :func:`_encode_operation_id`) instead of flattened,
        and ``.`` is escaped on the way so the emitted id splits back into
        exactly ``id``/``method``/``path``.
        """
        return (
            f"{_encode_operation_id(self.id)}."
            f"{method.lower()}."
            f"{_encode_operation_id(route.path)}"
        )

# EOF
