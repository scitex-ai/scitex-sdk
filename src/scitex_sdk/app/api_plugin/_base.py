#!/usr/bin/env python3
"""Closed vocabularies, grammar regexes and the contract error."""

from __future__ import annotations

import re

#: How the descriptors are implemented, stated where a reader will look. The
#: alternative (pydantic v2 models) would add a hard dependency to a package
#: whose base install is stdlib-only, so it is a published-install-surface
#: change and therefore the card owner's ruling rather than a silent choice.
DESCRIPTOR_IMPLEMENTATION = "stdlib-frozen-dataclasses"

#: The entry-point group a leaf publishes its API plugin under. Parallel to the
#: ``scitex.apps`` group in :mod:`scitex_sdk.app.plugins`: the value is read as a
#: STRING (nothing is imported until the host deliberately loads it), which is
#: what makes an installed package "trusted" rather than "arbitrary code".
API_ENTRY_POINT_GROUP = "scitex.apis"

#: HTTP methods a route may declare — the closed set the approval surface can
#: reason about. Anything else (a custom verb, a bare ``*``) is refused.
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

#: Methods that CHANGE state. A route using one of these must declare its
#: idempotency behaviour: a retried POST with no declared key is the
#: double-create the operator called out.
MUTATING_METHODS = ("POST", "PUT", "PATCH", "DELETE")

#: How a route answers. ``sse`` and ``binary`` are first-class because leaves
#: genuinely have them (measured on FigRecipe: a streaming chat endpoint and
#: ``download/{fmt}``) — a contract that only models JSON would make those
#: endpoints undescribable, which is how they end up undocumented.
TRANSPORTS = ("json", "sse", "binary")

#: JSON Schema's primitive type names. Borrowed rather than invented so the
#: generated OpenAPI fragment needs no translation table.
FIELD_TYPES = ("string", "integer", "number", "boolean", "object", "array")

#: Who a route's data belongs to. ``user`` and ``project`` reuse the vocabulary
#: already fixed by :mod:`scitex_sdk.app._app_scope`; ``none`` means the response is
#: not scoped to an actor at all (a public listing).
PROJECT_SCOPES = ("none", "user", "project")

#: Whether and how much of a call is recorded. The minimal honest vocabulary:
#: an endpoint either is not audited, records that a call happened, or records
#: the call and its actor-visible arguments.
AUDIT_LEVELS = ("none", "metadata", "full")

#: Pagination styles a route may declare.
PAGINATION_STYLES = ("none", "offset", "cursor")

#: Default header a client sends its idempotency key in.
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

#: Header names an idempotency key may NEVER be declared in, lowercased. An
#: idempotency key and an authentication credential (or a cookie, or a
#: framing/length field, or a hop-by-hop control) cannot share one header: the
#: message would have to carry two values with different meanings, and whichever
#: of the two the declaring client loses is a security or framing bug that the
#: declaration itself caused. Comparison is case-insensitive (HTTP field names
#: are), so ``Authorization`` and ``authorization`` are the same refusal.
RESERVED_IDEMPOTENCY_HEADERS = frozenset({
    "authorization",
    "proxy-authorization",
    "proxy-authenticate",
    "www-authenticate",
    "authentication-info",
    "proxy-authentication-info",
    "cookie",
    "set-cookie",
    "host",
    "content-length",
    "content-type",
    "content-encoding",
    "content-range",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "upgrade",
    "te",
    "trailer",
    "expect",
})

#: The security scheme every scoped operation's requirement names, and the
#: component the fragment declares it as. The scheme is an OAuth2
#: ``authorizationCode`` flow when it is emitted, because that is what the
#: requirement's value IS: an array of OAuth scopes. A scheme that carries a
#: scope array but declares no flows and no scope map would be a document that
#: names scopes it never defines, so the plugin has to declare the authorization
#: server it trusts (see :class:`OAuthProvider`) for a scoped requirement to be
#: emittable at all.
OAUTH_SECURITY_SCHEME = "scitexOAuth"

#: The OAuth2 flow name the emitted scheme uses: the one a native/agent client
#: with no secret can actually run (authorization code + PKCE). Declared here
#: rather than chosen per render, so the document says one thing.
OAUTH2_FLOW = "authorizationCode"

#: RECOMMENDED rate/quota classes — examples for the approved deployments, NOT
#: a closed enum. The hub ruled (2026-09-17) that a leaf may declare its own
#: extensible class, so these are documentation constants: a third-party plugin
#: is not refused for naming a class this module has never heard of, and the
#: approval surface compares against the deployment's own list.
RECOMMENDED_RATE_CLASSES = ("interactive", "standard", "bulk")

#: RECOMMENDED compute-cost declarations, same standing as the rate classes:
#: examples that make a declaration readable, quoted by the docs, not enforced.
RECOMMENDED_COMPUTE_COSTS = ("light", "standard", "heavy")

#: The contract major a declaration follows when it names none. Kept equal to
#: :data:`~.api_rules.CONTRACT_MAJOR`; a descriptor written before the field
#: existed therefore reads as contract 1, which is what it was built against.
DEFAULT_CONTRACT = "1"

_CONTRACT_RE = re.compile(r"^[1-9][0-9]*$")
_METHOD_RE = re.compile(r"^[A-Z]+$")
#: ``<package>.<resource>.<verb>``, each part lowercase kebab-case (API-O001).
_OPERATION_ID_RE = re.compile(
    r"^[a-z][a-z0-9]*(-[a-z0-9]+)*(\.[a-z][a-z0-9]*(-[a-z0-9]+)*){2}$"
)
_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")
_HANDLER_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_][\w.]*$")
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_PLACEHOLDER_RE = re.compile(r"^\{[A-Za-z_][\w]*\}$")

#: Any ``{placeholder}`` inside a path, for the COLLISION form (see
#: :func:`_canonical_path`): the placeholder's name does not distinguish two
#: paths for OpenAPI, so it must not distinguish two declarations here either.
_TEMPLATE_RE = re.compile(r"\{[A-Za-z_][\w]*\}")

#: OpenAPI's component-key pattern, verbatim: a component name, a schema name or
#: a JSON-Schema property name is read by generators as an identifier, and the
#: specification itself refuses anything outside this alphabet (``/``, ``~``,
#: whitespace, ``:``). Enforced at construction so a name that the document
#: validator would reject cannot be declared at all.
_COMPONENT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

#: RFC 7230 ``tchar`` — the ONLY characters an HTTP field name may contain.
#: A header name carrying CR, LF or any other control character lets a
#: declaration smuggle a second header past whatever client writes it, so the
#: whole token alphabet is enforced rather than only the obvious few.
_HTTP_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

#: RFC 3986 §3.2.2 ``reg-name`` — the alphabet a host is built from:
#: ``unreserved`` (``A-Za-z0-9-._~``) plus ``sub-delims``, so a DNS name (dots
#: and hyphens) and an internal hostname (``_``) need nothing extra, or else a
#: pct-encoded octet. A space, ``<``, ``|``, ``^``, a bracket or a non-ASCII
#: byte is outside it: a host the grammar does not accept is one no client can
#: resolve, whatever a permissive parser reported as ``netloc``.
_REG_NAME_RE = re.compile(r"^(?:[A-Za-z0-9\-._~!$&'()*+,;=]|%[0-9A-Fa-f]{2})+$")

#: RFC 3986 §3.2.3 spells ``port = *DIGIT``; made strict here, because a port a
#: declaration carries but a client cannot dial (empty, non-numeric, out of
#: range) is a promise the endpoint does not keep.
_PORT_RE = re.compile(r"^[0-9]+$")

#: RFC 3986 §2.1: ``pct-encoded = "%" HEXDIG HEXDIG``. A ``%`` that begins no
#: triplet leaves the escaping of the URI undefined, so a client cannot know
#: what the string it was handed means.
_PCT_SYNTAX_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")

#: Every pct-encoded octet, for the rule that a character refused RAW is
#: refused encoded as well: ``%0a`` smuggles the same CR/LF pair as a literal
#: one once a client hands the URL to its parser.
_PCT_OCTET_RE = re.compile(r"%([0-9A-Fa-f]{2})")

#: Every character a URI may contain (RFC 3986 §2.1-§2.3): ``unreserved``,
#: ``sub-delims``, the ``gen-delims`` that separate components, and ``%``.
#: Anything else — space, a control character, ``<``, ``>``, ``"``, ``{``,
#: ``}``, ``|``, ``\``, ``^``, a backtick, a non-ASCII byte — is not a URI
#: character, so a string carrying one is not a URI at all.
_URI_CHAR_RE = re.compile(r"^[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$")

#: The same alphabet for the PATH and QUERY, where ``[`` and ``]`` have no
#: meaning: they delimit the authority's IP-literal and nothing else, and the
#: fragment ``#`` is refused separately (RFC 6749 §3.1).
_PATH_QUERY_CHAR_RE = re.compile(r"^[A-Za-z0-9\-._~:/?@!$&'()*+,;=%]*$")

#: Characters that must never appear in a declared path. A path is a
#: DECLARATION that a host will compose into a real route, so anything that
#: could escape the mount, reach a shell, or smuggle a scheme is refused here
#: rather than trusted downstream ("no raw shell/path/argv").
_FORBIDDEN_PATH_CHARS = ("..", "//", "\\", " ", "\t", "\n", "?", "#", "%")


class ApiPluginContractError(ValueError):
    """A leaf's API declaration is malformed.

    Raised at construction: every condition this catches would otherwise ship an
    endpoint whose promise differs from what a client was told.
    """

# EOF
