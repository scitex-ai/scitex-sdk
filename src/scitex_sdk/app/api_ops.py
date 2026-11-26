#!/usr/bin/env python3
"""The OPERATION layer over :mod:`.api_plugin`: one declaration, every surface.

A leaf declares operations — a verb on a resource of its package — and this
module derives everything a client and a host rely on, mechanically, so no
leaf can spell them differently:

=============  =============================================================
URL            ``/api/v1/<package>/<resource>[/{<resource_singular>_id}][/<action>]``
               (the ROUTE is relative, ``<resource>...``; the host mounts the
               plugin at ``api/v1/<package>/``)
method/status  list/get GET 200 · create POST 201 · update PATCH 200 ·
               delete DELETE 204 · action POST 200 (202 + job when async)
scope          ``<package>:<resource>:read`` for list/get, ``:write`` otherwise
MCP tool       ``<package>_<resource>_<verb>`` (``-`` -> ``_``)
operation id   ``<package>.<resource>.<verb>``
project id     project-scoped operations take ``project`` = ``owner/slug``
pagination     cursor: ``?limit=&cursor=`` -> ``{data, next_cursor, has_more}``
errors         RFC 9457 problem+json (see :mod:`.api_serve`)
=============  =============================================================

The result is an ordinary :class:`~.api_plugin.ApiPlugin` of
:class:`~.api_plugin.ApiRoute` objects — the existing, validated contract —
and :func:`operation_of` reads the operation back from any route, so the
serving adapter and the MCP generator need nothing but the plugin.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from .api_plugin import (
    ApiError,
    ApiField,
    ApiPlugin,
    ApiPluginContractError,
    ApiRoute,
    ApiSchema,
    AuthScope,
    Idempotency,
    OAuthProvider,
    Pagination,
    RateLimit,
)

API_PREFIX = "api/v1"
#: Verbs with fixed semantics; anything else is an ACTION verb.
CRUD_VERBS = {
    # verb: (method, on an item?, access)
    "list": ("GET", False, "read"),
    "get": ("GET", True, "read"),
    "create": ("POST", False, "write"),
    "update": ("PATCH", True, "write"),
    "delete": ("DELETE", True, "write"),
}
#: The response schema name that marks an asynchronous operation (202 + job).
JOB_SCHEMA = "Job"
#: The request field every project-scoped operation takes.
PROJECT_FIELD = ApiField("project", "string", True, "Project id as owner/slug")
CURSOR_FIELDS = (
    ApiField("limit", "integer", False, "Page size"),
    ApiField("cursor", "string", False, "Opaque cursor from next_cursor"),
)
DEFAULT_OAUTH_BASE = "https://scitex.ai/oauth"

_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def _name(value: str, what: str) -> str:
    if not isinstance(value, str) or not _NAME_RE.match(value):
        raise ApiPluginContractError(
            f"{what} {value!r} must be lowercase kebab-case ([a-z][a-z0-9-]*)"
        )
    return value


def singular(resource: str) -> str:
    """``datasets`` -> ``dataset``; ``cache-entries`` -> ``cache_entry``."""
    word = resource.replace("-", "_")
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s"):
        return word[:-1]
    return word


@dataclass(frozen=True)
class ApiOperation:
    """A verb on a resource of a package: the unit REST and MCP share.

    ``verb`` is a CRUD verb (see :data:`CRUD_VERBS`) or an action name; an
    action is ``item=True`` (``POST <resource>/{id}/<verb>``) or a collection
    action (``POST <resource>/<verb>``). ``read_only`` marks an action with no
    side effects (scope ``read``, no idempotency key). ``params`` are the
    query (GET) or body (other methods) fields; ``project`` and the cursor
    fields are added automatically.
    """

    package: str
    resource: str
    verb: str
    handler: str
    summary: str = ""
    params: Sequence[ApiField] = field(default_factory=tuple)
    response: ApiSchema | None = None
    errors: Sequence[ApiError] = field(default_factory=tuple)
    item: bool | None = None
    read_only: bool = False
    project_scoped: bool = False
    paginated: bool = False
    default_limit: int = 20
    max_limit: int = 100
    rate_class: str = "standard"
    compute_cost: str = "light"

    def __post_init__(self) -> None:
        _name(self.package, "package")
        _name(self.resource, "resource")
        _name(self.verb, "verb")
        if not self.resource.endswith("s"):
            raise ApiPluginContractError(
                f"resource {self.resource!r} must be a plural noun"
            )
        if self.verb in CRUD_VERBS:
            if self.item is not None and self.item != CRUD_VERBS[self.verb][1]:
                raise ApiPluginContractError(
                    f"verb {self.verb!r} fixes item={CRUD_VERBS[self.verb][1]}"
                )
            if self.read_only:
                raise ApiPluginContractError("read_only applies to action verbs only")
        elif self.item is None:
            raise ApiPluginContractError(
                f"action {self.verb!r} must state item=True or item=False"
            )
        if self.paginated and self.verb != "list":
            raise ApiPluginContractError("only a list operation is paginated")

    # ---------------------------------------------------------------- derived
    @property
    def is_item(self) -> bool:
        return CRUD_VERBS[self.verb][1] if self.verb in CRUD_VERBS else bool(self.item)

    @property
    def method(self) -> str:
        return CRUD_VERBS[self.verb][0] if self.verb in CRUD_VERBS else "POST"

    @property
    def access(self) -> str:
        if self.verb in CRUD_VERBS:
            return CRUD_VERBS[self.verb][2]
        return "read" if self.read_only else "write"

    @property
    def id_param(self) -> str | None:
        return f"{singular(self.resource)}_id" if self.is_item else None

    @property
    def path(self) -> str:
        parts = [self.resource]
        if self.is_item:
            parts.append("{" + self.id_param + "}")
        if self.verb not in CRUD_VERBS:
            parts.append(self.verb)
        return "/".join(parts)

    @property
    def url(self) -> str:
        return f"/{API_PREFIX}/{self.package}/{self.path}"

    @property
    def scope(self) -> str:
        return f"{self.package}:{self.resource}:{self.access}"

    @property
    def mcp_name(self) -> str:
        return f"{self.package}_{self.resource}_{self.verb}".replace("-", "_")

    @property
    def operation_id(self) -> str:
        return f"{self.package}.{self.resource}.{self.verb}"

    @property
    def is_async(self) -> bool:
        return self.response is not None and self.response.name == JOB_SCHEMA

    @property
    def success_status(self) -> int:
        if self.is_async:
            return 202
        return {"create": 201, "delete": 204}.get(self.verb, 200)

    def request_fields(self) -> tuple:
        fields = list(self.params)
        names = {f.name for f in fields}
        if self.project_scoped and "project" not in names:
            fields.insert(0, PROJECT_FIELD)
        if self.paginated:
            fields.extend(f for f in CURSOR_FIELDS if f.name not in names)
        return tuple(fields)

    def route(self) -> ApiRoute:
        fields = self.request_fields()
        request = ApiSchema(self._schema_name("Request"), fields) if fields else None
        return ApiRoute(
            path=self.path,
            methods=(self.method,),
            rate=RateLimit(self.rate_class, self.compute_cost),
            path_params=(self.id_param,) if self.is_item else (),
            request=request,
            response=self.response,
            errors=tuple(self.errors),
            auth=AuthScope(
                project_scope="project" if self.project_scoped else "user",
                scopes=(self.scope,),
            ),
            idempotency=Idempotency(required=self.access == "write"),
            pagination=(
                Pagination("cursor", self.default_limit, self.max_limit)
                if self.paginated
                else Pagination()
            ),
            handler=self.handler,
            read_only=self.read_only,
            summary=self.summary,
        )

    def _schema_name(self, suffix: str) -> str:
        words = [self.package, self.resource, self.verb]
        camel = "".join(w.replace("-", " ").title().replace(" ", "") for w in words)
        return f"{camel}{suffix}"


def build_plugin(
    package: str,
    title: str,
    api_version: str,
    operations: Sequence[ApiOperation],
    *,
    oauth_base: str = DEFAULT_OAUTH_BASE,
) -> ApiPlugin:
    """The :class:`ApiPlugin` of ``operations`` (all of one ``package``).

    The OAuth provider is derived too: every operation's scope is declared
    with a description, so the plugin's scope catalogue is complete by
    construction.
    """
    _name(package, "package")
    operations = tuple(operations)
    if not operations:
        raise ApiPluginContractError(f"package {package!r} declares no operations")
    for op in operations:
        if not isinstance(op, ApiOperation) or op.package != package:
            raise ApiPluginContractError(
                f"operation {op!r} does not belong to package {package!r}"
            )
    names = [op.mcp_name for op in operations]
    if len(set(names)) != len(names):
        raise ApiPluginContractError(f"package {package!r} declares an operation twice")
    scopes = {}
    for op in operations:
        scopes[op.scope] = f"{op.access.title()} {op.resource} of {package}"
    return ApiPlugin(
        id=package,
        title=title,
        api_version=api_version,
        routes=tuple(op.route() for op in operations),
        oauth=OAuthProvider(
            authorization_url=f"{oauth_base}/authorize/",
            token_url=f"{oauth_base}/token/",
            scopes=scopes,
        ),
    )


def operation_of(plugin: ApiPlugin, route: ApiRoute) -> ApiOperation:
    """Read the operation back from one of ``plugin``'s routes.

    Raises :class:`ApiPluginContractError` for a route that does not follow
    the operation grammar (it was not built by :func:`build_plugin`).
    """
    segments = route.path.split("/")
    resource = segments[0]
    rest = segments[1:]
    item = bool(rest) and rest[0].startswith("{")
    action = rest[-1] if rest and not rest[-1].startswith("{") else None
    method = route.methods[0]
    if action is not None:
        verb = action
    else:
        verb = next(
            (
                v
                for v, (m, on_item, _) in CRUD_VERBS.items()
                if m == method and on_item == item
            ),
            None,
        )
        if verb is None:
            raise ApiPluginContractError(f"route {route.path!r} is not an operation")
    fields = tuple(route.request.fields) if route.request else ()
    implicit = {"project"} if route.auth.project_scope == "project" else set()
    if route.pagination.style == "cursor":
        implicit |= {"limit", "cursor"}
    op = ApiOperation(
        package=plugin.id,
        resource=resource,
        verb=verb,
        handler=route.handler,
        summary=route.summary,
        params=tuple(f for f in fields if f.name not in implicit),
        response=route.response,
        errors=tuple(route.errors),
        item=None if verb in CRUD_VERBS else item,
        read_only=route.read_only if verb not in CRUD_VERBS else False,
        project_scoped=route.auth.project_scope == "project",
        paginated=route.pagination.style == "cursor",
        default_limit=route.pagination.default_limit or 20,
        max_limit=route.pagination.max_limit or 100,
        rate_class=route.rate.rate_class,
        compute_cost=route.rate.compute_cost,
    )
    if op.path != route.path or (op.scope,) != tuple(route.auth.scopes):
        raise ApiPluginContractError(
            f"route {route.path!r} does not match its derived operation "
            f"({op.path!r}, scope {op.scope!r})"
        )
    return op


def operations(plugin: ApiPlugin) -> tuple:
    """Every operation of ``plugin``, in declaration order."""
    return tuple(operation_of(plugin, route) for route in plugin.routes)


def scope_granted(required: str, granted: Sequence[str]) -> bool:
    """Whether ``granted`` scopes cover ``required`` (``pkg:resource:access``).

    Wildcards: ``*`` (everything), ``*:read`` / ``*:write`` (any package),
    ``pkg:*`` / ``pkg:*:read`` (any resource of a package), and ``write``
    implies ``read`` for the same resource.
    """
    package, resource, access = required.split(":")
    accepted = {
        "*",
        f"*:{access}",
        f"{package}:*",
        f"{package}:*:{access}",
        f"{package}:{resource}:{access}",
        f"{package}:{resource}:*",
    }
    if access == "read":
        accepted |= {"*:write", f"{package}:*:write", f"{package}:{resource}:write"}
    return any(scope in accepted for scope in granted)


__all__ = [
    "API_PREFIX",
    "CRUD_VERBS",
    "JOB_SCHEMA",
    "ApiOperation",
    "build_plugin",
    "operation_of",
    "operations",
    "scope_granted",
    "singular",
]
