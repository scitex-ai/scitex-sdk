#!/usr/bin/env python3
"""Opt-in admission for leaf API plugins: declare first, enable explicitly, import last.

A host decision binds an exact discovered :class:`ApiPluginRef` (name,
target, distribution) plus the accepted source to an explicit enabled path
set. Only an admitted reference may be resolved to a callable, and only for
an enabled path — every check runs on strings BEFORE any import, so an
unreviewed module's import side effects can never fire during discovery,
listing, or denied activation. There is no default enablement: an empty
enabled set admits nothing.

For display without execution, :func:`dump_inert_descriptor` serializes an
:class:`ApiPlugin` to validated JSON and :func:`read_inert_descriptor`
reads it back from a distribution's installed metadata WITHOUT importing
the leaf package. Absent inert data stays unknown; it never justifies
loading a callable for inspection.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from . import api_plugin
from .api_plugin import ApiPlugin, ApiPluginRef, ApiRoute

INERT_DESCRIPTOR_FILENAME = "scitex_api.json"


class AdmissionDenied(Exception):
    """A leaf API was requested without a matching explicit admission."""


@dataclass(frozen=True)
class ApiAdmission:
    """The host's authoritative enablement for one discovered plugin ref.

    ``review_ref`` is the host's opaque review identifier (which review
    granted this) — deliberately NOT an artifact attestation: it names the
    decision, never the bytes. Artifact identity stays with the
    distribution/target strings the host verified out of band.
    """

    name: str
    distribution: str
    target: str
    review_ref: str
    enabled: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for slot in ("name", "target", "review_ref"):
            value = getattr(self, slot)
            if not isinstance(value, str) or not value.strip():
                raise AdmissionDenied(f"admission {slot} must be a nonempty string")
        if not isinstance(self.distribution, str):
            raise AdmissionDenied("admission distribution must be a string")
        paths = []
        for path in self.enabled:
            paths.append(api_plugin._validate_path(path))
        object.__setattr__(self, "enabled", tuple(paths))


def admit(
    ref: ApiPluginRef, *, review_ref: str, enabled: Iterable[str]
) -> ApiAdmission:
    """Bind the host decision for one discovered ref. No imports happen here."""
    return ApiAdmission(
        name=ref.name,
        distribution=ref.distribution,
        target=ref.target,
        review_ref=review_ref,
        enabled=tuple(enabled),
    )


def _import_dotted(target: str, *, expect_callable: bool = False) -> Any:
    """Import ``module:attr.path`` with failures mapped to denial, not bare errors.

    Nested attributes (``Class.method``) walk down from the module. With
    ``expect_callable``, the final object must be callable, otherwise a data
    object could be returned under the handler contract; plugin declaration
    objects themselves are data and must not pass through that gate.
    """
    from importlib import import_module

    module_name, _, attr_path = target.partition(":")
    if not module_name or not attr_path:
        raise AdmissionDenied(f"unresolvable handler target: {target!r}")
    try:
        obj: Any = import_module(module_name)
    except ImportError as exc:
        raise AdmissionDenied(f"cannot import {module_name!r}") from exc
    try:
        for part in attr_path.split("."):
            obj = getattr(obj, part)
    except AttributeError as exc:
        raise AdmissionDenied(f"{module_name!r} has no {attr_path!r}") from exc
    if expect_callable and not callable(obj):
        raise AdmissionDenied(f"{target!r} is not callable")
    return obj


def require_admitted(ref: ApiPluginRef, admission: ApiAdmission) -> None:
    """Enforce the admission decision before any model/code import.

    A host calls this at settings time, before Django setup imports the
    plugin's AppConfig and models: identity drift raises
    :class:`AdmissionDenied` while no leaf code has loaded. Per-path
    enablement is still checked at :func:`resolve_handler`.
    """
    if (
        ref.name != admission.name
        or ref.target != admission.target
        or ref.distribution != admission.distribution
    ):
        raise AdmissionDenied("admission does not match the discovered reference")


def resolve_handler(
    ref: ApiPluginRef, admission: ApiAdmission, path: str, method: str = "GET"
) -> Callable:
    """Return the handler callable for one ``(path, method)`` route.

    Routes are keyed by path AND method: a method-disjoint GET/POST pair on
    one path resolves each side separately. Order is the contract:
    ref/admission identity, then path membership, then — and only then —
    the first import. Anything else (identity drift, disabled path,
    undeclared pair, unresolvable or non-callable handler) raises
    :class:`AdmissionDenied` before or without running leaf code beyond
    the admitted target.
    """
    if (
        ref.name != admission.name
        or ref.target != admission.target
        or ref.distribution != admission.distribution
    ):
        raise AdmissionDenied("admission does not match the discovered reference")
    require_admitted(ref, admission)
    wanted = api_plugin._validate_path(path)
    if wanted not in admission.enabled:
        raise AdmissionDenied(f"path {wanted!r} is not enabled")
    plugin = _import_dotted(ref.target)
    if not isinstance(plugin, ApiPlugin):
        raise AdmissionDenied(f"{ref.target!r} is not an API plugin declaration")
    wanted_method = method.upper()
    for route in plugin.routes:
        if route.path == wanted and wanted_method in route.methods:
            return _import_dotted(route.handler, expect_callable=True)
    raise AdmissionDenied(f"route {(wanted, wanted_method)!r} is not declared")


def _convert(hint: Any, value: Any, what: str) -> Any:
    """Convert one inert value toward its declared slot type, strictly."""
    import types
    import typing

    if hint is None or hint is Any:
        return value
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if origin is typing.Union or (isinstance(origin, type) and origin is types.UnionType) or str(origin) == "typing.Union":
        options = [a for a in args if a is not type(None)]
        if value is None:
            return None
        if len(options) == 1:
            return _convert(options[0], value, what)
        for option in options:
            try:
                return _convert(option, value, what)
            except AdmissionDenied:
                continue
        raise AdmissionDenied(f"no union option fits {what}")
    if origin is not None:
        import collections.abc as _abc

        if issubclass(origin, _abc.Mapping):
            if not isinstance(value, dict):
                raise AdmissionDenied(f"{what} must be an object")
            key_hint = args[0] if len(args) > 0 else Any
            value_hint = args[1] if len(args) > 1 else Any
            return {
                _convert(key_hint, k, f"{what}<key>"): _convert(value_hint, v, f"{what}[{k}]")
                for k, v in value.items()
            }
        if not isinstance(value, list):
            raise AdmissionDenied(f"{what} must be a list")
        items = [_convert(args[0], v, f"{what}[]") for v in value] if args else list(value)
        return tuple(items) if origin is tuple else items
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        return _build(hint, value)
    return value


def _build(cls: Any, data: Any) -> Any:
    """Reconstruct a validated dataclass from inert data, strictly."""
    import typing

    if not isinstance(data, dict):
        raise AdmissionDenied(
            f"cannot rebuild {getattr(cls, '__name__', cls)} from {type(data).__name__}"
        )
    try:
        hints = typing.get_type_hints(cls)
    except Exception as exc:
        raise AdmissionDenied(
            f"cannot inspect {getattr(cls, '__name__', cls)}"
        ) from exc
    declared = {f.name for f in dataclasses.fields(cls)}
    unknown = set(data) - declared
    if unknown:
        raise AdmissionDenied(
            f"unknown {getattr(cls, '__name__', cls)} fields: {sorted(unknown)}"
        )
    kwargs: dict[str, Any] = {}
    for name, value in data.items():
        kwargs[name] = _convert(hints.get(name), value, f"{getattr(cls, '__name__', cls)}.{name}")
    try:
        return cls(**kwargs)
    except AdmissionDenied:
        raise
    except Exception as exc:
        raise AdmissionDenied(
            f"invalid {getattr(cls, '__name__', cls)} data: {exc}"
        ) from exc


def dump_inert_descriptor(plugin: ApiPlugin) -> str:
    """Serialize a validated plugin declaration to inert JSON text."""
    if not isinstance(plugin, ApiPlugin):
        raise AdmissionDenied("can only serialize an ApiPlugin declaration")
    return json.dumps(dataclasses.asdict(plugin), sort_keys=True, indent=1)


def read_inert_descriptor(distribution: str) -> Optional[ApiPlugin]:
    """Read a leaf's inert descriptor from installed metadata, no imports.

    Returns the validated :class:`ApiPlugin`, or None when the
    distribution carries no descriptor. Anything malformed raises
    :class:`AdmissionDenied` — an unreadable descriptor never falls back
    to loading code for inspection.
    """
    try:
        from importlib import metadata as _metadata
    except ImportError as exc:
        raise AdmissionDenied("importlib.metadata is unavailable") from exc
    try:
        dist = _metadata.distribution(distribution)
    except _metadata.PackageNotFoundError:
        return None
    except Exception as exc:
        raise AdmissionDenied(
            f"cannot locate distribution {distribution!r}: {exc}"
        ) from exc
    try:
        text = dist.read_text(INERT_DESCRIPTOR_FILENAME)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise AdmissionDenied(f"cannot read inert descriptor: {exc}") from exc
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise AdmissionDenied("inert descriptor is not valid JSON") from exc
    return _build(ApiPlugin, data)


__all__ = [
    "INERT_DESCRIPTOR_FILENAME",
    "AdmissionDenied",
    "ApiAdmission",
    "admit",
    "dump_inert_descriptor",
    "read_inert_descriptor",
    "require_admitted",
    "resolve_handler",
]


# EOF
