#!/usr/bin/env python3
"""Closed vocabularies and the decided limits profiles (contract §12.1, §12.4)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from ..api_plugin import EXPOSURES  # API-K001, the declaration's closed set

#: API-Q001: priority classes, highest first.
PRIORITY_CLASSES = ("paid", "member", "public")
#: The usage kind a sponsored call is rated under (API-K005).
SPONSORED_USAGE_KIND = "public_compute"
#: The flags of API-K003, in report order.
EXCEEDED_FLAGS = ("cpu", "memory", "wall", "bytes", "storage_write", "external")

_KIB = 1024
_MIB = 1024 * _KIB


def setting(name: str, default=None):
    """A Django setting, or ``default`` when Django is not configured."""
    try:
        from django.conf import settings
    except ImportError:  # pragma: no cover - django is a dependency
        return default
    if not settings.configured:
        return default
    return getattr(settings, name, default)


_HOOKS: dict = {}


def hook(name: str):
    """The host hook ``name``: an object, or a dotted path / class built ONCE.

    A dotted path or a class is resolved and instantiated once per distinct
    setting value, so a stateful hook (an in-memory idempotency store, a
    limiter) keeps its state across requests.
    """
    value = setting(name)
    if value is None:
        return None
    if not isinstance(value, (str, type)):
        return value
    key = (name, value)
    if key not in _HOOKS:
        resolved = value
        if isinstance(value, str):
            from django.utils.module_loading import import_string

            resolved = import_string(value)
        _HOOKS[key] = resolved() if isinstance(resolved, type) else resolved
    return _HOOKS[key]


@dataclass(frozen=True)
class LimitsProfile:
    """Per-call (or per-job) limits of one class of work.

    ``None`` means "not bounded by this profile". ``asynchronous`` marks a
    profile whose operations answer a Job: the request then holds no slot and
    the leaf's job runner owns the pool. ``extra`` carries profile-specific
    caps a handler reads by name (``max_panels``, ``max_pages`` ...).
    """

    name: str
    max_request_bytes: int | None = None
    max_values: int | None = None
    cpu_seconds: float | None = None
    memory_bytes: int | None = None
    wall_seconds: float | None = None
    max_response_bytes: int | None = None
    asynchronous: bool = False
    extra: Mapping = field(default_factory=dict)

    def get(self, name: str, default=None):
        """A cap by name: a declared attribute or an ``extra`` entry."""
        if name in self.extra:
            return self.extra[name]
        return getattr(self, name, default)

    def as_dict(self) -> dict:
        out = {
            "name": self.name,
            "max_request_bytes": self.max_request_bytes,
            "max_values": self.max_values,
            "cpu_seconds": self.cpu_seconds,
            "memory_bytes": self.memory_bytes,
            "wall_seconds": self.wall_seconds,
            "max_response_bytes": self.max_response_bytes,
            "asynchronous": self.asynchronous,
        }
        out.update(self.extra)
        return out


#: The decided profiles (decision 10, 2026-11-28). ``light`` is API-K002.
PROFILES = {
    "light": LimitsProfile(
        "light",
        max_request_bytes=256 * _KIB,
        cpu_seconds=1.0,
        memory_bytes=256 * _MIB,
        wall_seconds=5.0,
        max_response_bytes=1 * _MIB,
    ),
    "stats-inline": LimitsProfile(
        "stats-inline",
        max_request_bytes=4 * _MIB,
        max_values=100_000,
        cpu_seconds=2.0,
        memory_bytes=512 * _MIB,
        wall_seconds=10.0,
        max_response_bytes=1 * _MIB,
    ),
    "stats-bootstrap": LimitsProfile(
        "stats-bootstrap",
        max_request_bytes=4 * _MIB,
        max_values=100_000,
        cpu_seconds=30.0,
        memory_bytes=1024 * _MIB,
        wall_seconds=30.0,
        max_response_bytes=1 * _MIB,
        extra={"max_n_boot": 10_000},
    ),
    "figure-inline": LimitsProfile(
        "figure-inline",
        max_request_bytes=8 * _MIB,
        max_values=100_000,
        cpu_seconds=20.0,
        memory_bytes=1024 * _MIB,
        wall_seconds=20.0,
        # base64 of a 5 MB image plus the envelope
        max_response_bytes=7 * _MIB,
        extra={"max_panels": 12, "max_output_bytes": 5_000_000},
    ),
    "pdf-compile-public": LimitsProfile(
        "pdf-compile-public",
        # base64 of a 20 MB bundle plus the envelope
        max_request_bytes=28 * _MIB,
        cpu_seconds=240.0,
        memory_bytes=2048 * _MIB,
        wall_seconds=120.0,
        max_response_bytes=1 * _MIB,
        asynchronous=True,
        extra={
            "max_bundle_bytes": 20_000_000,
            "max_files": 200,
            "max_pages": 50,
            "max_pdf_bytes": 20_000_000,
            "cpus": 2,
            "slots": 2,
        },
    ),
}


def profiles() -> dict:
    """The built-in profiles, overlaid with ``SCITEX_API_LIMITS_PROFILES``."""
    out = dict(PROFILES)
    for name, spec in (setting("SCITEX_API_LIMITS_PROFILES") or {}).items():
        if isinstance(spec, LimitsProfile):
            out[name] = spec
        else:
            out[name] = replace(out.get(name, LimitsProfile(name)), **dict(spec))
    return out


def profile_for(op) -> LimitsProfile | None:
    """The profile an operation's cost class implies.

    ``light`` is concrete (API-K002); ``standard`` and ``heavy`` are bounded by
    the leaf's own limits, so they imply no profile here.
    """
    return profiles()["light"] if op.compute_cost == "light" else None


__all__ = [
    "EXCEEDED_FLAGS",
    "EXPOSURES",
    "PRIORITY_CLASSES",
    "PROFILES",
    "SPONSORED_USAGE_KIND",
    "LimitsProfile",
    "hook",
    "profile_for",
    "profiles",
    "setting",
]
