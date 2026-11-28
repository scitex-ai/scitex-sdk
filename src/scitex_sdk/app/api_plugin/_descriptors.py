#!/usr/bin/env python3
"""Leaf descriptors of a route: fields, schemas, errors, auth and promises."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ._base import (
    AUDIT_LEVELS,
    EXPOSURES,
    FIELD_TYPES,
    IDEMPOTENCY_KEY_HEADER,
    PAGINATION_STYLES,
    PROJECT_SCOPES,
    RESERVED_IDEMPOTENCY_HEADERS,
    ApiPluginContractError,
)
from ._validators import (
    _require_choice,
    _require_component_name,
    _require_elements,
    _require_text,
    _require_text_or_empty,
    _require_token,
    _require_version,
    _strip_all,
)


@dataclass(frozen=True)
class ApiField:
    """One declared field of a request or response body."""

    name: str
    type: str = "string"
    required: bool = True
    description: str = ""
    enum: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # The validated form IS the stored form, for every value below: each
        # validator returns the normalized value and its result is assigned
        # (see _strip_all). Storing the declared value instead is how a padded
        # name was checked and then emitted unchanged.
        object.__setattr__(
            self, "name", _require_component_name(self.name, "field name")
        )
        object.__setattr__(
            self, "type", _require_choice(self.type, FIELD_TYPES, "field type")
        )
        if not isinstance(self.required, bool):
            raise ApiPluginContractError(
                f"field {self.name!r} has a non-boolean required flag "
                f"({self.required!r})"
            )
        object.__setattr__(self, "description", _require_text_or_empty(
            self.description, f"description of field {self.name!r}"
        ))
        object.__setattr__(self, "enum", _strip_all(
            _require_elements(self.enum, str, f"enum of field {self.name!r}"),
            f"enum member of field {self.name!r}",
        ))


@dataclass(frozen=True)
class ApiSchema:
    """A named body schema: strict, and never empty.

    An empty schema is refused because it is ambiguous — "takes nothing" and
    "nobody wrote it down" read the same to a client generator. The name must be
    a valid OpenAPI component key (see :func:`_require_component_name`): it
    becomes ``components.schemas[<name>]`` and the schema's ``title``, and the
    validator refuses a key outside ``[a-zA-Z0-9._-]``.
    """

    name: str
    fields: Sequence[ApiField] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # The validated form IS the stored form (see _strip_all): the component
        # key the validator approved is the one emitted, not the declared one.
        object.__setattr__(
            self, "name", _require_component_name(self.name, "schema name")
        )
        object.__setattr__(self, "fields", _require_elements(
            self.fields, ApiField, f"fields of schema {self.name!r}"
        ))
        if not self.fields:
            raise ApiPluginContractError(
                f"schema {self.name!r} declares no fields; an empty schema "
                "cannot be told apart from an undocumented body"
            )
        seen: list[str] = []
        for item in self.fields:
            if item.name in seen:
                raise ApiPluginContractError(
                    f"schema {self.name!r} declares field {item.name!r} twice"
                )
            seen.append(item.name)


@dataclass(frozen=True)
class ApiError:
    """One structured error a route may return.

    Structured on purpose: a bare ``{error: str}`` gives a client nothing to
    branch on, and leaves retry-vs-dont-retry to string matching (measured on
    FigRecipe's endpoints today).
    """

    code: str
    status: int
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        # Stored stripped, not merely checked stripped: these three reach the
        # document (the code and message under `x-scitex-errors`).
        object.__setattr__(self, "code", _require_text(self.code, "error code"))
        object.__setattr__(
            self, "message", _require_text(self.message, "error message")
        )
        if not isinstance(self.status, int) or isinstance(self.status, bool):
            raise ApiPluginContractError(
                f"error {self.code!r} has a non-integer status ({self.status!r})"
            )
        if not 400 <= self.status <= 599:
            raise ApiPluginContractError(
                f"error {self.code!r} declares status {self.status}; an error a "
                "client sees must be a 4xx or 5xx"
            )
        if not isinstance(self.retryable, bool):
            raise ApiPluginContractError(
                f"error {self.code!r} has a non-boolean retryable flag "
                f"({self.retryable!r}); a client cannot act on an ambiguous one"
            )


def _check_exposure(auth) -> None:
    """Resolve and validate ``AuthScope.exposure`` (API-K001)."""
    if auth.exposure is None:
        default = "public_eligible" if auth.public else "member"
        object.__setattr__(auth, "exposure", default)
    _require_choice(auth.exposure, EXPOSURES, "auth exposure")
    if auth.public and auth.exposure != "public_eligible":
        raise ApiPluginContractError(
            f"auth declares public=True with exposure={auth.exposure!r}; an "
            "always-public route is public_eligible by definition"
        )
    if auth.exposure == "public_eligible" and auth.project_scope == "project":
        raise ApiPluginContractError(
            "auth declares exposure='public_eligible' on a project-scoped route; "
            "a route that reaches project data has the ceiling 'member'"
        )


@dataclass(frozen=True)
class AuthScope:
    """What a caller must present, and whose data the route touches.

    ``scopes`` are OAuth/OIDC scope strings. A route with NO scope is refused
    unless it says so explicitly with ``public=True``: forgetting to declare a
    scope must not silently open an endpoint, which is the fail-closed rule this
    whole contract rests on. ``public=True`` in turn REQUIRES
    ``project_scope="none"``: a public route is not user- or project-scoped, and
    a public declaration that claims to be would tell a client that a listing is
    filtered by an actor when it is not. Native clients authenticate with
    authorization-code + PKCE against these scopes — the contract never carries
    a client secret, because nothing here can hold one.

    ``exposure`` is the route's ceiling for a host's public tier (API-K001):
    only ``public_eligible`` may be enabled for anonymous callers by host
    configuration; ``member`` and ``privileged`` never. Omitted, it is
    ``public_eligible`` for a ``public=True`` route and ``member`` otherwise.
    """

    project_scope: str = "user"
    scopes: Sequence[str] = field(default_factory=tuple)
    public: bool = False
    session: bool = False
    exposure: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_scope", _require_choice(
            self.project_scope, PROJECT_SCOPES, "auth project_scope"
        ))
        object.__setattr__(self, "scopes", _strip_all(
            _require_elements(self.scopes, str, "auth scopes"),
            "auth scope",
        ))
        if not isinstance(self.public, bool):
            raise ApiPluginContractError(
                f"auth public flag must be a boolean (got {self.public!r})"
            )
        if not isinstance(self.session, bool):
            raise ApiPluginContractError(
                f"auth session flag must be a boolean (got {self.session!r})"
            )
        if self.session and (self.scopes or self.public):
            raise ApiPluginContractError(
                "auth declares session=True together with scopes or public=True; "
                "a session-cookie route carries no OAuth scopes and is not open — "
                "exactly one of session/scopes/public describes it"
            )
        if not self.public and not self.scopes and not self.session:
            raise ApiPluginContractError(
                "an auth scope declares neither scopes nor public=True nor "
                "session=True; a route whose auth was never stated must not be "
                "treated as open. Declare the OAuth scopes it needs, say "
                "public=True out loud, or mark the native session cookie with "
                "session=True."
            )
        if self.public and self.scopes:
            raise ApiPluginContractError(
                f"auth declares public=True together with scopes "
                f"{tuple(self.scopes)}; exactly one of the two describes it"
            )
        if self.public and self.project_scope != "none":
            raise ApiPluginContractError(
                f"auth declares public=True with project_scope="
                f"{self.project_scope!r}; a public route is not scoped to an "
                "actor or a project at all, so declare project_scope='none' — "
                "anything else advertises a listing as filtered when it is not"
            )
        _check_exposure(self)


@dataclass(frozen=True)
class Idempotency:
    """The route's retry promise.

    ``required=True`` means the caller MUST send a key (default header
    :data:`IDEMPOTENCY_KEY_HEADER`) and the endpoint guarantees no second
    effect for a replayed key. ``key_header`` must be a valid HTTP field name:
    a name carrying CR, LF or any other control character would let the
    declaration smuggle a second header into the request the client writes.

    ``key_header`` may not name a RESERVED header (:data:`RESERVED_IDEMPOTENCY_HEADERS`)
    either. ``Authorization`` is the case that matters: the client sends the
    bearer credential there, and a header carrying both one credential and one
    idempotency key is a header whose second value the server drops — so either
    the credential or the retry guarantee silently stops working. A reserved
    name is compared case-insensitively, because HTTP field names are.
    """

    required: bool = False
    key_header: str = IDEMPOTENCY_KEY_HEADER

    def __post_init__(self) -> None:
        if not isinstance(self.required, bool):
            raise ApiPluginContractError(
                f"idempotency required flag must be a boolean (got {self.required!r})"
            )
        header = _require_token(self.key_header, "idempotency key header")
        if header.lower() in RESERVED_IDEMPOTENCY_HEADERS:
            raise ApiPluginContractError(
                f"idempotency key header {self.key_header!r} is RESERVED; it "
                "already carries an authentication credential, a cookie, a "
                "framing/length value or a hop-by-hop control, so one header "
                "cannot carry that AND an idempotency key. Declare a header of "
                f"the route's own, such as {IDEMPOTENCY_KEY_HEADER!r}."
            )
        object.__setattr__(self, "key_header", header)


@dataclass(frozen=True)
class Pagination:
    """The route's list-envelope promise."""

    style: str = "none"
    default_limit: int | None = None
    max_limit: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "style", _require_choice(
            self.style, PAGINATION_STYLES, "pagination style"
        ))
        for label, value in (("default_limit", self.default_limit), ("max_limit", self.max_limit)):
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ApiPluginContractError(
                    f"pagination {label} must be a positive integer (got {value!r})"
                )
        if self.style == "none":
            if self.default_limit is not None or self.max_limit is not None:
                raise ApiPluginContractError(
                    "pagination declares limits with style='none'; the route "
                    "would advertise a page size it does not implement"
                )
            return
        if self.default_limit is None or self.max_limit is None:
            raise ApiPluginContractError(
                f"pagination style {self.style!r} needs BOTH default_limit and "
                "max_limit; an unbounded page size is what makes a list "
                "endpoint unbounded for the client that builds against it"
            )
        if self.default_limit > self.max_limit:
            raise ApiPluginContractError(
                f"pagination default_limit {self.default_limit} exceeds "
                f"max_limit {self.max_limit}"
            )


@dataclass(frozen=True)
class RateLimit:
    """The route's rate/quota class and its declared compute cost.

    Both are REQUIRED and non-blank, and whitespace-only is refused — but the
    vocabulary is EXTENSIBLE rather than closed, per the hub's ruling
    (2026-09-17): a third-party plugin must not be rejected for naming a class
    this module has never heard of, so the approval surface compares a
    declaration against the DEPLOYMENT's own approved list.
    :data:`RECOMMENDED_RATE_CLASSES` and :data:`RECOMMENDED_COMPUTE_COSTS` are
    the documented examples a leaf should reach for first, and the ones the
    generated OpenAPI fragment's ``x-scitex-rate-class`` /
    ``x-scitex-compute-cost`` extensions will carry.
    """

    rate_class: str
    compute_cost: str
    quota_note: str = ""

    def __post_init__(self) -> None:
        # Both reach the document as x-scitex-rate-class / x-scitex-compute-cost,
        # so the approved (stripped) value is the stored one.
        object.__setattr__(
            self, "rate_class", _require_text(self.rate_class, "rate_class")
        )
        object.__setattr__(
            self, "compute_cost", _require_text(self.compute_cost, "compute_cost")
        )
        object.__setattr__(self, "quota_note", _require_text_or_empty(
            self.quota_note, "rate quota_note"
        ))


@dataclass(frozen=True)
class Audit:
    """Whether a call is recorded, and how much of it."""

    level: str = "metadata"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "level", _require_choice(self.level, AUDIT_LEVELS, "audit level")
        )


@dataclass(frozen=True)
class Deprecation:
    """The route's version window: when it goes, and what replaces it.

    A deprecation with a sunset but no replacement is allowed (an endpoint can
    simply end); a deprecation with no sunset is refused, because it is the
    announcement that never arrives at the client.
    """

    sunset_version: str
    replacement: str | None = None

    def __post_init__(self) -> None:
        # Both are emitted (deprecated / x-scitex-sunset-version /
        # x-scitex-replacement), so both are stored in validated form.
        object.__setattr__(self, "sunset_version", _require_version(
            self.sunset_version, "deprecation sunset_version"
        ))
        if self.replacement is not None:
            object.__setattr__(self, "replacement", _require_text(
                self.replacement, "deprecation replacement"
            ))

# EOF
