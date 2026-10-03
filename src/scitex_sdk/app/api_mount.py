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
    """The host's authoritative enablement for one discovered plugin ref."""

    name: str
    distribution: str
    target: str
    source: str
    enabled: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for slot in ("name", "target", "source"):
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
    ref: ApiPluginRef, *, source: str, enabled: Iterable[str]
) -> ApiAdmission:
    """Bind the host decision for one discovered ref. No imports happen here."""
    return ApiAdmission(
        name=ref.name,
        distribution=ref.distribution,
        target=ref.target,
        source=source,
        enabled=tuple(enabled),
    )


def _import_dotted(target: str) -> Any:
    """Import ``module:attribute`` with failures mapped to denial, not bare errors."""
    from importlib import import_module

    module_name, _, attr = target.partition(":")
    if not module_name or not attr:
        raise AdmissionDenied(f"unresolvable handler target: {target!r}")
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise AdmissionDenied(f"cannot import {module_name!r}") from exc
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise AdmissionDenied(f"{module_name!r} has no {attr!r}") from exc


def resolve_handler(
    ref: ApiPluginRef, admission: ApiAdmission, path: str
) -> Callable:
    """Return the handler callable for ``path`` under an explicit admission.

    Order is the contract: ref/admission identity, then path membership,
    then — and only then — the first import. Anything else (identity
    drift, disabled path, unknown route, unresolvable handler) raises
    :class:`AdmissionDenied` before or without running leaf code beyond
    the admitted target.
    """
    if (
        ref.name != admission.name
        or ref.target != admission.target
        or ref.distribution != admission.distribution
    ):
        raise AdmissionDenied("admission does not match the discovered reference")
    wanted = api_plugin._validate_path(path)
    if wanted not in admission.enabled:
        raise AdmissionDenied(f"path {wanted!r} is not enabled")
    plugin = _import_dotted(ref.target)
    if not isinstance(plugin, ApiPlugin):
        raise AdmissionDenied(f"{ref.target!r} is not an API plugin declaration")
    for route in plugin.routes:
        if route.path == wanted:
            return _import_dotted(route.handler)
    raise AdmissionDenied(f"path {wanted!r} is not declared")


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
        text = _metadata.distribution(distribution).read_text(
            INERT_DESCRIPTOR_FILENAME
        )
    except Exception:
        return None
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
    "resolve_handler",
]


# EOF
