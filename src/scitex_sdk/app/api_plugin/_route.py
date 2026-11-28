#!/usr/bin/env python3
"""One declared endpoint (ApiRoute) and the rule for what a duplicate is."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from urllib.parse import quote

from ._base import (
    _HANDLER_RE,
    _METHOD_RE,
    _PLACEHOLDER_RE,
    _TEMPLATE_RE,
    HTTP_METHODS,
    MUTATING_METHODS,
    TRANSPORTS,
    ApiPluginContractError,
)
from ._descriptors import (
    ApiError,
    ApiSchema,
    Audit,
    AuthScope,
    Deprecation,
    Idempotency,
    Pagination,
    RateLimit,
)
from ._validators import (
    _require_choice,
    _require_elements,
    _require_text,
    _require_text_or_empty,
    _strip_all,
    _validate_path,
)


@dataclass(frozen=True)
class ApiRoute:
    """One declared endpoint: what it takes, returns, needs and promises.

    ``rate`` is REQUIRED and has no default on purpose. An omitted rate class
    would be filled in by whoever reads the missing value — the deployment's
    most permissive bucket, or its most expensive one — and the leaf would never
    have agreed to it. Every route states its own class and compute cost.
    """

    path: str
    methods: Sequence[str]
    rate: RateLimit
    path_params: Sequence[str] = field(default_factory=tuple)
    request: ApiSchema | None = None
    response: ApiSchema | None = None
    errors: Sequence[ApiError] = field(default_factory=tuple)
    auth: AuthScope = field(default_factory=AuthScope)
    idempotency: Idempotency = field(default_factory=Idempotency)
    pagination: Pagination = field(default_factory=Pagination)
    audit: Audit = field(default_factory=Audit)
    transport: str = "json"
    handler: str = ""
    deprecation: Deprecation | None = None
    read_only: bool = False
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _validate_path(self.path))
        object.__setattr__(self, "summary", _require_text_or_empty(
            self.summary, f"summary of route {self.path!r}"
        ))
        if not isinstance(self.rate, RateLimit):
            raise ApiPluginContractError(
                f"route {self.path!r} declares rate {self.rate!r}, a "
                f"{type(self.rate).__name__}; expected a RateLimit"
            )
        for slot, declared, expected in (
            ("auth", self.auth, AuthScope),
            ("idempotency", self.idempotency, Idempotency),
            ("pagination", self.pagination, Pagination),
            ("audit", self.audit, Audit),
        ):
            if not isinstance(declared, expected):
                raise ApiPluginContractError(
                    f"{slot} of route {self.path!r} is {declared!r}, a "
                    f"{type(declared).__name__}; expected an instance of "
                    f"{expected.__name__} — a dict that happens to carry the "
                    "right keys is refused HERE, by name, rather than reaching "
                    "fragment generation as an AttributeError that names the "
                    "renderer instead of the declaration"
                )
        if self.deprecation is not None and not isinstance(self.deprecation, Deprecation):
            raise ApiPluginContractError(
                f"deprecation of route {self.path!r} is {self.deprecation!r}, a "
                f"{type(self.deprecation).__name__}; expected an instance of "
                "Deprecation or None"
            )
        object.__setattr__(self, "path_params", _strip_all(
            _require_elements(
                self.path_params, str, f"path_params of route {self.path!r}"
            ),
            f"path parameter of route {self.path!r}",
        ))
        methods = _require_elements(
            self.methods, str, f"methods of route {self.path!r}"
        )
        if not methods:
            raise ApiPluginContractError(
                f"route {self.path!r} declares no methods"
            )
        for method in methods:
            if not _METHOD_RE.match(method):
                raise ApiPluginContractError(
                    f"route {self.path!r} declares method {method!r}; expected "
                    f"an uppercase HTTP method from {HTTP_METHODS}"
                )
            _require_choice(method, HTTP_METHODS, f"method of route {self.path!r}")
        if len(set(methods)) != len(methods):
            raise ApiPluginContractError(
                f"route {self.path!r} declares a method twice"
            )
        object.__setattr__(self, "methods", methods)
        object.__setattr__(self, "transport", _require_choice(
            self.transport, TRANSPORTS, f"transport of route {self.path!r}"
        ))
        for slot, schema in (("request", self.request), ("response", self.response)):
            if schema is not None and not isinstance(schema, ApiSchema):
                raise ApiPluginContractError(
                    f"{slot} of route {self.path!r} is {schema!r}, a "
                    f"{type(schema).__name__}; expected an ApiSchema or None"
                )
        object.__setattr__(self, "errors", _require_elements(
            self.errors, ApiError, f"errors of route {self.path!r}"
        ))
        # Stripped FIRST and then matched, so the string the rule approved is
        # the string stored — and the one emitted as x-scitex-handler.
        handler = _require_text(self.handler, f"handler of route {self.path!r}")
        if not _HANDLER_RE.match(handler):
            raise ApiPluginContractError(
                f"route {self.path!r} declares handler {self.handler!r}; expected "
                "an entry-point-style 'module.path:attr' — a declaration, never "
                "a shell command, a filesystem path or argv"
            )
        object.__setattr__(self, "handler", handler)
        self._refuse_undeclared_mutation()
        self._refuse_duplicate_errors()
        self._refuse_undeclared_path_params()

    def _refuse_undeclared_path_params(self) -> None:
        """The declared ``path_params`` and the path's ``{placeholders}`` match.

        A ``{param}`` nobody declared is a parameter no client can supply and no
        generator can name; a declaration with no ``{param}`` behind it is a
        parameter the route claims to take and can never receive. Refusing both
        keeps the fragment's ``parameters`` list exactly equal to the path
        template the host will serve.
        """
        declared = list(self.path_params)
        # Each name was already validated and STORED stripped in __post_init__,
        # so this method only has to compare the declaration against the path's
        # {placeholders}.
        if len(set(declared)) != len(declared):
            raise ApiPluginContractError(
                f"route {self.path!r} declares a path parameter twice; one "
                "parameter cannot be described two ways"
            )
        in_path = _path_placeholders(self.path)
        repeated = [name for name in in_path if in_path.count(name) > 1]
        if repeated:
            raise ApiPluginContractError(
                f"route {self.path!r} uses placeholder {repeated[0]!r} more "
                "than once; one operation cannot declare the same path "
                "parameter twice, and two segments cannot be constrained by "
                "one value"
            )
        missing = [name for name in in_path if name not in declared]
        if missing:
            raise ApiPluginContractError(
                f"route {self.path!r} uses placeholder(s) {tuple(missing)} that "
                "are not declared in path_params; an undeclared path parameter "
                "reaches a client as an argument it was never told to send"
            )
        extra = [name for name in declared if name not in in_path]
        if extra:
            raise ApiPluginContractError(
                f"route {self.path!r} declares path_params {tuple(extra)} that "
                "do not appear as {placeholder} segments in its path; the route "
                "would promise a parameter it can never receive"
            )

    def _refuse_undeclared_mutation(self) -> None:
        """A mutating route must state its idempotency behaviour.

        Silence here is the expensive kind: a retried POST creates a second
        object, and the client had no way to know it was unsafe.

        ``read_only=True`` exempts POST alone: a query-semantics POST has no
        side effects, so there is nothing a retry could duplicate. PUT, PATCH
        and DELETE are inherently mutating and still require the key, and a
        read-only route declaring them is refused outright.
        """
        mutating = [m for m in self.methods if m in MUTATING_METHODS]
        if not isinstance(self.read_only, bool):
            raise ApiPluginContractError(
                f"route {self.path!r} declares read_only {self.read_only!r}; "
                "expected a boolean"
            )
        if self.read_only:
            stubborn = [m for m in mutating if m != "POST"]
            if stubborn:
                raise ApiPluginContractError(
                    f"route {self.path!r} declares read_only with {tuple(stubborn)}; "
                    "only POST can be side-effect free, the rest always mutate"
                )
            mutating = []
        if mutating and not self.idempotency.required:
            raise ApiPluginContractError(
                f"route {self.path!r} accepts {tuple(mutating)} but declares no "
                "required idempotency key; a retried mutating call would act "
                "twice. Declare Idempotency(required=True) and honour the key, "
                "or drop the mutating method."
            )

    def _refuse_duplicate_errors(self) -> None:
        """Two errors with one code cannot be told apart by a client."""
        seen: list[str] = []
        for error in self.errors:
            if error.code in seen:
                raise ApiPluginContractError(
                    f"route {self.path!r} declares error code {error.code!r} "
                    "twice; a client branches on the code"
                )
            seen.append(error.code)

    @property
    def key(self) -> tuple[str, str]:
        """``(path, method)`` pairs are declared one at a time: see ``route_keys``."""
        return (self.path, self.methods[0])

    def route_keys(self) -> tuple[tuple[str, str], ...]:
        """Every ``(path, method)`` this route claims — the uniqueness unit."""
        return tuple((self.path, method) for method in self.methods)


def _normalize_path(path: str) -> str:
    """The COMPARISON form of a declared path: trailing slashes stripped.

    A declared path is already required to be normalized (a trailing ``/`` is
    refused by :func:`_validate_path`), so two keys that differ here cannot both
    exist. Normalizing anyway keeps the uniqueness rule below independent of
    which spelling a future declaration used.
    """
    return path.rstrip("/")


def _canonical_path(path: str) -> str:
    """The COLLISION form of a declared path: one token per placeholder.

    OpenAPI keys paths by TEMPLATE, and two templates differing only by a
    placeholder's NAME are the SAME path: ``/things/{id}`` and
    ``/things/{name}`` occupy one slot, so a host merging both would keep one
    operation and drop the other — silently, because neither declaration was
    wrong on its own. Replacing every ``{placeholder}`` with one canonical token
    (``{}``) makes the two collide HERE, where the refusal can name both
    declarations, rather than inside a merged document with no author left to
    tell. Comparison is case-sensitive: OpenAPI paths are.
    """
    return _TEMPLATE_RE.sub("{}", _normalize_path(path))


#: How a declared name or an operationId component is spelled. PERCENT-ENCODING
#: (``quote`` with nothing marked safe) is a bijection, which is the property
#: that matters: the previous lossy ``path.replace("/", "_")`` mapped
#: ``a/b_c`` and ``a_b/c`` onto ONE id and published two operations under it,
#: which the document validator then refused. ``.`` is escaped as well (urlquote
#: leaves it alone, since it is unreserved in a URI) so the emitted id contains
#: exactly two dots and splits back into ``id``/``method``/``path`` with no
#: ambiguity — that is what makes the id injective over the whole triple, not
#: merely over the path within one plugin.
_OPERATION_ID_ESCAPE_CHAR = "%2E"


def _encode_operation_id(text: str) -> str:
    """The injective ``operationId`` spelling of a declared name or path.

    ``urllib.parse.quote`` with an empty ``safe`` set percent-encodes every
    character outside the unreserved set, including ``/`` (so ``a/b_c`` becomes
    ``a%2Fb_c`` and cannot be confused with ``a_b%2Fc``); the ``.`` substitution
    afterwards keeps the method separator unambiguous.
    """
    return quote(text, safe="").replace(".", _OPERATION_ID_ESCAPE_CHAR)


def _path_placeholders(path: str) -> tuple[str, ...]:
    """Every ``{param}`` a declared path uses, in declaration order."""
    return tuple(
        segment[1:-1] for segment in path.split("/") if _PLACEHOLDER_RE.match(segment)
    )


def _declared_schemas(route: ApiRoute) -> tuple[tuple[str, ApiSchema], ...]:
    """``(role, schema)`` for every body ``route`` declares, absent ones dropped."""
    pairs = (("request", route.request), ("response", route.response))
    return tuple((role, schema) for role, schema in pairs if schema is not None)


def _operation_claims(
    routes: Sequence[ApiRoute], plugin_id: str
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    """Check every route's ``(canonical path, method)`` claim; return the claims.

    ONE definition of "a duplicate", called by construction
    (:meth:`ApiPlugin._refuse_duplicate_route_keys`) AND by the renderer
    (:meth:`ApiPlugin.openapi_fragment`), so the two cannot disagree about what
    a collision is — they did, and that disagreement was the bug: the model
    accepted ``GET x`` and ``POST x`` as two routes while the renderer refused
    the second.

    The unit is the OPERATION — one canonical path PLUS one method — not the
    path. ``GET x`` and ``POST x`` are two operations on ONE OpenAPI Path Item
    (they are one URL), so they merge; the same path AND the same method twice
    is the genuine collision, because the host can compose only one operation
    there and the loser would vanish without a trace.

    The one thing that cannot merge is a canonical path whose declarations
    disagree about the SPELLING of its placeholders (``things/{id}`` as GET and
    ``things/{name}`` as POST). OpenAPI keys both as one path, so one merged
    item would carry one template while the other route's parameters name a
    path variable that template does not contain — an operation no validator
    resolves. That is refused here, where both declarations can still be named.

    Returns the claimed ``(canonical path, method)`` pairs mapped to their owner
    (the collision message needs it) and the canonical path's declared spelling
    (the Path Item key the renderer emits, so a merge has exactly one).
    """
    claims: dict[tuple[str, str], str] = {}
    spellings: dict[str, str] = {}
    for route in routes:
        canonical = _canonical_path(route.path)
        for method in route.methods:
            key = (canonical, method)
            owner = claims.get(key)
            if owner is not None:
                raise ApiPluginContractError(
                    f"api plugin {plugin_id!r} declares {method} {route.path} "
                    f"twice ({owner} and {method} {route.path}); the host can "
                    "compose only one operation per path and method, so the "
                    "other would vanish without a trace. Two templates that "
                    "differ only by a placeholder's NAME are the same OpenAPI "
                    "path, not two."
                )
            claims[key] = f"{method} {route.path}"
        declared = spellings.get(canonical)
        if declared is not None and declared != route.path:
            raise ApiPluginContractError(
                f"api plugin {plugin_id!r} declares {route.path!r} and "
                f"{declared!r}, which OpenAPI keys as ONE path ({canonical!r}): "
                "a placeholder's NAME does not distinguish two templates, so "
                "two routes cannot be merged into one Path Item under two "
                "spellings — the emitted template would name one of them and "
                f"the other route's parameters would reference a path variable "
                f"it does not contain. Declare {declared!r}."
            )
        spellings[canonical] = route.path
    return claims, spellings

# EOF
