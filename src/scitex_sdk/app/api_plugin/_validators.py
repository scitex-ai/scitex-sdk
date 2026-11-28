#!/usr/bin/env python3
"""Value validators shared by every descriptor: text, tokens, URLs, paths."""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from urllib.parse import urlsplit

from ._base import (
    _COMPONENT_NAME_RE,
    _FORBIDDEN_PATH_CHARS,
    _HTTP_TOKEN_RE,
    _PATH_QUERY_CHAR_RE,
    _PATH_SEGMENT_RE,
    _PCT_OCTET_RE,
    _PCT_SYNTAX_RE,
    _PLACEHOLDER_RE,
    _PORT_RE,
    _REG_NAME_RE,
    _URI_CHAR_RE,
    _VERSION_RE,
    ApiPluginContractError,
)


def _require_text(value: object, what: str) -> str:
    """Return ``value`` stripped, or raise when it is not non-blank text."""
    if not isinstance(value, str) or not value.strip():
        raise ApiPluginContractError(
            f"{what} must be a non-blank string (got {value!r}); an empty "
            f"{what} is indistinguishable from an undeclared one"
        )
    return value.strip()


def _require_text_or_empty(value: object, what: str) -> str:
    """Return ``value`` stripped when it is a string — empty allowed, else raise.

    The optional-text rule: an ABSENT description and an undescribed one read
    the same, so ``""`` is fine, but a non-string is not. ``description: 5``
    would otherwise be copied verbatim into the generated JSON Schema, where the
    specification requires a string: one wrong type at the declaration site
    becomes a document the host's own tooling rejects.
    """
    if not isinstance(value, str):
        raise ApiPluginContractError(
            f"{what} must be a string (got {value!r}, a "
            f"{type(value).__name__}); a non-string reaches the generated "
            "document as an invalid value rather than as prose"
        )
    return value.strip()


def _strip_all(values: Sequence[str], what: str) -> tuple[str, ...]:
    """Every element of ``values``, validated AND returned stripped.

    This is the fix for the defect class a review found here: a validator that
    returns the NORMALIZED value while the dataclass keeps the DECLARED one.
    ``_require_text`` has always returned the stripped text, but every call site
    that discarded the return value declared one thing and STORED another, so a
    padded value was checked and then emitted unchanged. Assigning the result
    makes the stored element BE the validated element — there is no later
    "strip on the way out" that could be forgotten, because there is no later
    strip at all.
    """
    return tuple(_require_text(value, what) for value in values)


def _require_component_name(value: object, what: str) -> str:
    """Return ``value`` if it is a valid OpenAPI component key, else raise.

    OpenAPI's own pattern for a component key is ``^[a-zA-Z0-9._-]+$``: a name
    carrying ``/``, ``~``, whitespace, ``:`` or ``%`` is not merely ugly, it is
    a document the specification refuses (measured: openapi-spec-validator
    rejects ``Bad/Name`` on the component-key pattern). The same alphabet is
    required of a JSON-Schema property name, because a generator reads both as
    identifiers from one flat namespace.
    """
    text = _require_text(value, what)
    if not _COMPONENT_NAME_RE.match(text):
        raise ApiPluginContractError(
            f"{what} {value!r} is not a valid OpenAPI component name; it must "
            "be one or more of the characters a-zA-Z0-9._- and may not contain "
            "'/', '~', ':', '%', whitespace or any other character a "
            "specification-compliant consumer refuses"
        )
    return text


def _require_choice(value: object, choices: Sequence[str], what: str) -> str:
    """Return ``value`` if it is one of ``choices``, else raise."""
    if value not in choices:
        raise ApiPluginContractError(
            f"{what} must be one of {tuple(choices)} (got {value!r}); a value "
            "outside the closed set cannot be rendered or enforced"
        )
    return str(value)


def _require_token(value: object, what: str) -> str:
    """Return ``value`` if it is a valid HTTP field-name token, else raise.

    Refuses CR, LF, every other control character, spaces and ``:`` by refusing
    any character outside RFC 7230 ``tchar``. Whitespace-only already fails the
    blank check; this is the injection case, where a "header name" is really a
    header name plus a second header.
    """
    text = _require_text(value, what)
    if not _HTTP_TOKEN_RE.match(text):
        raise ApiPluginContractError(
            f"{what} {value!r} is not a valid HTTP field name; it must be one "
            "or more RFC 7230 tchar and must not contain CR, LF or any other "
            "control character (a name that can carry one can smuggle a second "
            "header), nor a space or ':'"
        )
    return text


def _require_oauth_endpoint_url(value: object, label: str) -> str:
    """Return the RAW endpoint URL once the whole string is an RFC 3986 URI.

    THE TRAP THIS CLOSES IS THE PARSER'S OWN NORMALIZATION. CPython's
    ``urlsplit`` deletes every C0 control, every DEL and any leading whitespace
    from the string it parses — ``urlsplit`` of a URL whose path is
    ``/oa<LF>uth`` reports the path ``/oauth`` — so a check written against the
    parsed components accepts a declaration whose RAW text still carries the
    control character, and the raw text is exactly what this descriptor stores
    and what the document emits as ``authorizationUrl``/``tokenUrl``. Every
    rule below therefore reads the RAW string, and the parse is required to
    AGREE with it (scheme, authority and host alike) before the string is
    stored.

    Refused by name: any control character (``ord < 0x20`` or ``0x7f``) or any
    whitespace character anywhere in the string, padding included (an RFC 3986
    URI carries neither, so neither can be normalized away); any non-ASCII
    character (a URI is ASCII, so an internationalised endpoint has to be
    declared percent-encoded or in punycode); a fragment (``#``, which
    RFC 6749 §3.1 forbids on an endpoint URI); a ``%`` that begins no
    pct-encoded octet; a pct-encoded control character (a character refused raw
    is refused encoded); any character outside the URI alphabet; a scheme other
    than http/https; a string whose parse disagrees with its own text; a
    missing authority; a userinfo credential; a host outside RFC 3986; ``[`` or
    ``]`` outside the authority; and a port that is not a number in 1..65535
    (see :func:`_require_endpoint_host`).
    """
    if not isinstance(value, str) or not value.strip():
        raise ApiPluginContractError(
            f"OAuth {label} must be a non-blank string (got {value!r}); an "
            f"empty OAuth {label} is indistinguishable from an undeclared one"
        )
    text = value
    for index, char in enumerate(text):
        codepoint = ord(char)
        if codepoint < 0x20 or codepoint == 0x7F:
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} carries the control character "
                f"{char!r} at index {index}; the endpoint is emitted verbatim, "
                "and urlsplit deletes the controls and spaces it PARSEs, so "
                "this one would be validated as absent and published as "
                "present"
            )
        if char.isspace():
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} carries whitespace ({char!r}) at "
                f"index {index}; an RFC 3986 URI has none, so neither padding "
                "nor a space inside the hostname can be normalized away — the "
                "string a client is handed has to be the string that was "
                "validated"
            )
        if codepoint > 0x7E:
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} carries the non-ASCII character "
                f"{char!r} at index {index}; RFC 3986 URIs are ASCII, so an "
                "internationalised endpoint has to be declared in its "
                "percent-encoded (or punycode) form for a client to call it"
            )
    if "#" in text:
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} carries a fragment ('#'); RFC 6749 §3.1 "
            "forbids a fragment in an endpoint URI, and a client that resolved "
            "one would call an address the authorization server never "
            "described"
        )
    if _PCT_SYNTAX_RE.search(text):
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} carries a '%' that begins no pct-encoded "
            "octet (RFC 3986: pct-encoded = '%' HEXDIG HEXDIG); the escaping "
            "of the URI is undefined, so a client cannot construct the request"
        )
    for match in _PCT_OCTET_RE.finditer(text):
        octet = int(match.group(1), 16)
        if octet <= 0x20 or octet == 0x7F:
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} pct-encodes the control character "
                f"{octet:#04x}; a character this contract refuses RAW is "
                "refused encoded too, because the endpoint is one string that "
                "a client hands to a URL parser"
            )
    if not _URI_CHAR_RE.match(text):
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} carries a character RFC 3986 permits "
            "nowhere in a URI; the alphabet is unreserved, sub-delims, the "
            "gen-delims that separate components and pct-encoded octets, and "
            "nothing else"
        )
    try:
        parts = urlsplit(text)
    except ValueError as exc:
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} is not a parseable URL: {exc}"
        ) from exc
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} is not an absolute http(s) URL; a "
            "flow endpoint a client must call has to name its scheme "
            "and host, and it is declared here rather than invented by "
            "the fragment renderer"
        )
    marker = len(parts.scheme) + 3
    if text[:marker].lower() != f"{parts.scheme}://":
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} does not parse to itself: the parse "
            f"reports the scheme {parts.scheme!r}, so the declaration has to "
            f"begin with {parts.scheme + '://'!r} (compared case-insensitively "
            "— RFC 3986 §3.1 makes the scheme case-insensitive)"
        )
    authority = text[marker:].split("/", 1)[0].split("?", 1)[0]
    if authority != parts.netloc:
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} declares the authority {authority!r} "
            f"while its parse reports {parts.netloc!r}; a component the parser "
            "does not recover from the raw string is one a client cannot "
            "resolve, and this contract stores and emits the raw string"
        )
    if not _PATH_QUERY_CHAR_RE.match(text[marker + len(authority) :]):
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} carries '[' or ']' outside its "
            "authority; those two characters delimit an IP-literal host and "
            "mean nothing anywhere else in an http(s) URI"
        )
    hostname = _require_endpoint_host(authority, label, value)
    # RE-MEASURED, on the string that IS stored: the components validated above
    # are the components a client recovers from it. This is what keeps the RAW
    # string the subject of the contract — should a later urlsplit normalize
    # something else out of (or into) its result, the parse and the stored text
    # stop agreeing and the declaration is refused instead of published.
    reparsed = urlsplit(text)
    # HOSTS ARE COMPARED CASE-INSENSITIVELY, AND ONLY THE HOST (fifth review,
    # 2026-09-17). Measured: `urlsplit` preserves the case it is handed whenever
    # the host contains a percent escape — `https://ex%2Fample.example/…` and
    # `https://%41BC.example/…` both come back with their case intact — while
    # this module lowercases the raw host for its reg-name grammar check. RFC
    # 3986 §3.2.2 makes the host case-insensitive (and §2.1 makes a percent
    # triplet's hex digits case-insensitive), so a case difference here is NOT a
    # round-trip failure and must not refuse a valid endpoint. The RAW declared
    # string is still what is stored and emitted; this comparison only stops
    # host case deciding a URL's validity. Authority and scheme are compared as
    # parsed: netloc round-trips verbatim (no normalisation either side), and
    # the scheme is already lowercased by both.
    if (
        reparsed.scheme,
        reparsed.netloc,
        (reparsed.hostname or "").lower(),
    ) != (
        parts.scheme,
        authority,
        hostname,
    ):
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} does not round-trip through urlsplit: "
            f"its parse reports the scheme {reparsed.scheme!r}, authority "
            f"{reparsed.netloc!r} and host {reparsed.hostname!r} while the "
            f"declared string carries the scheme {parts.scheme!r}, authority "
            f"{authority!r} and host {hostname!r}; the endpoint is emitted as "
            "one string, so its parse and its text have to be the same thing"
        )
    return text


def _require_endpoint_host(authority: str, label: str, value: object) -> str:
    """Return the hostname of a RAW authority, or refuse it under RFC 3986.

    The authority grammar is ``[ userinfo "@" ] host [ ":" port ]``
    (RFC 3986 §3.2). USERINFO is refused rather than accepted: this URL is
    published inside the generated document, so a ``client_id:secret@`` baked
    into it is a credential leak, and no OAuth endpoint needs one. The host is
    then required to be a ``reg-name`` (:data:`_REG_NAME_RE`) or a bracketed
    IPv6 literal — RFC 3986's two forms of ``host`` — and a port the
    declaration carries has to be one a client can dial. The hostname is
    returned as ``urlsplit().hostname`` reports it (lowercased, brackets
    removed) so the caller can require the parse to agree with the raw text.
    """
    if "@" in authority:
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} carries userinfo ('@'); the endpoint is "
            "emitted inside the generated document, where a credential baked "
            "into the URL is a leak rather than an authentication"
        )
    if authority.startswith("["):
        closing = authority.find("]")
        tail = authority[closing + 1 :] if closing != -1 else ""
        if closing == -1 or (tail and not tail.startswith(":")):
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} authority {authority!r} is not a "
                "host with an optional port: a bracketed IP-literal has to be "
                "closed by ']' and followed by ':port' or by nothing"
            )
        literal = authority[1:closing]
        port = tail[1:] if tail else None
        hostname = literal.lower()
        if "%" in literal:
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} authority {authority!r} carries a "
                "zone id; a scoped link-local address names an interface on "
                "one machine, which is not an endpoint another client can call"
            )
        try:
            ipaddress.IPv6Address(literal)
        except ValueError as exc:
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} authority {authority!r} is not a "
                "bracketed IPv6 literal (RFC 3986 IP-literal); nothing else "
                "may stand inside the brackets, and a bracketed IPv4 address "
                "is not an IP-literal either"
            ) from exc
    else:
        host, separator, port = authority.rpartition(":")
        if not separator:
            host, port = authority, None
        hostname = host.lower()
        if not _REG_NAME_RE.match(host):
            raise ApiPluginContractError(
                f"OAuth {label} {value!r} host {host!r} is not an RFC 3986 "
                "reg-name (unreserved / sub-delims / pct-encoded); a host "
                "outside the grammar is one a client cannot resolve"
            )
    if port is not None and (
        not _PORT_RE.match(port) or not 1 <= int(port) <= 65535
    ):
        raise ApiPluginContractError(
            f"OAuth {label} {value!r} authority {authority!r} carries the port "
            f"{port!r}; RFC 3986 spells a port as digits, and a port a "
            "declaration carries has to be complete and in 1..65535, because a "
            "client dials it"
        )
    return hostname


def _require_elements(value: object, element_type: type, what: str) -> tuple:
    """Return ``value`` as a tuple whose every element IS an ``element_type``.

    STRICT ON SHAPE AND ON ORDER. ``value`` must be a
    :class:`collections.abc.Sequence`, which refuses four kinds of near-miss:

    * a ``str``/``bytes``, because iterating it yields CHARACTERS — ``"abc"``
      where ``["a", "b", "c"]`` was meant declares three scopes nobody named;
    * a ``dict``/``set``/``frozenset``, because the iteration order of a set is
      an implementation detail of the hash seed, so one declaration would
      render a different document in a different process;
    * a generator or other iterator, because it is CONSUMED by the first render:
      the second call sees an empty sequence and silently emits nothing;
    * a single element where a sequence was declared.

    Strict by ``isinstance`` rather than by shape as well. A duck-typed
    stand-in (a dict that happens to carry ``name``/``type``, an ``int`` where a
    descriptor was meant) would otherwise be accepted here and blow up later as
    an AttributeError three frames into a renderer — naming nothing the leaf can
    fix. The refusals below name the FIELD, the offending TYPE and, for an
    element, its position, so the declaration site is obvious from the message
    alone.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ApiPluginContractError(
            f"{what} must be a sequence of {element_type.__name__} (got "
            f"{value!r}, a {type(value).__name__}); a single value where a "
            "sequence was declared is refused rather than iterated element by "
            "element, and a str, bytes, dict, set, frozenset, generator or "
            "other iterator is refused because its elements, or their order, "
            "are not a stable declaration"
        )
    items = tuple(value)
    for index, item in enumerate(items):
        if not isinstance(item, element_type):
            raise ApiPluginContractError(
                f"{what} element {index} is {item!r}, a "
                f"{type(item).__name__}; expected an instance of "
                f"{element_type.__name__} — a value that merely looks like one "
                "is not one"
            )
    return items


def _require_version(value: object, what: str) -> str:
    """Return a dotted version string, or raise."""
    text = _require_text(value, what)
    if not _VERSION_RE.match(text):
        raise ApiPluginContractError(
            f"{what} must be a dotted version such as '1' or '1.2' (got "
            f"{value!r}); a non-numeric version cannot be ordered against a "
            "sunset or a client's supported range"
        )
    return text


def _validate_path(path: object) -> str:
    """A route path declaration: relative, no traversal, no shell surface.

    Refused: a leading ``/`` (the host owns the mount prefix — a route that
    names an absolute path is claiming the root, which is exactly the "no root
    route registration" rule), ``..``, ``.`` as a whole segment, ``//``,
    backslashes, whitespace, query or fragment characters, percent-encoding, and
    any segment that is neither a plain name nor a ``{placeholder}``.
    """
    text = _require_text(path, "route path")
    if text.startswith("/"):
        raise ApiPluginContractError(
            f"route path {text!r} is absolute; declare it RELATIVE to the app "
            "(the host owns the mount prefix, and a leaf claiming a root route "
            "is the root-registration this contract forbids)"
        )
    for bad in _FORBIDDEN_PATH_CHARS:
        if bad in text:
            raise ApiPluginContractError(
                f"route path {text!r} contains {bad!r}; a declared path must "
                "not be able to encode traversal, a query, a fragment or a "
                "shell token"
            )
    if text.endswith("/"):
        raise ApiPluginContractError(
            f"route path {text!r} is not in NORMALIZED form: it ends in '/', so "
            f"two declarations of one endpoint would differ by a single "
            f"character and collide only downstream. Declare "
            f"{text.rstrip('/')!r} instead."
        )
    for segment in text.split("/"):
        if segment == ".":
            raise ApiPluginContractError(
                f"route path {text!r} has a '.' segment; RFC 3986 normalization "
                "removes a dot segment, so two declarations of one endpoint "
                "could differ only by a segment the host discards"
            )
        if _PATH_SEGMENT_RE.match(segment) or _PLACEHOLDER_RE.match(segment):
            continue
        raise ApiPluginContractError(
            f"route path {text!r} has segment {segment!r}; expected a plain "
            "name or a {placeholder}"
        )
    return text

# EOF
