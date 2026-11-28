#!/usr/bin/env python3
"""The public-tier configuration ``SCITEX_API_PUBLIC_TIER`` (API-K008).

Keys are operation ids; each entry says whether the operation is public today,
under which limits profile, and whether a key is required (``"key"``: any key
holder may call it, anonymous callers may not). The configuration can only
NARROW: an entry for an operation whose declared ``exposure`` ceiling is not
``public_eligible`` is refused loudly and the operation stays non-public
(API-K001).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import scitex_logging as slogging

from ._profiles import LimitsProfile, profiles, setting

_LOG = slogging.getLogger(__name__)
_KEYS = {"public", "limits", "requires", "priority"}


class PublicTierConfigError(ValueError):
    """``SCITEX_API_PUBLIC_TIER`` is malformed (a deploy-config error)."""


@dataclass(frozen=True)
class TierEntry:
    """One operation enabled in the public tier."""

    operation_id: str
    limits: LimitsProfile
    #: ``"key"``: callable by any key holder but not anonymously.
    requires: str | None = None


def _parse(config: Mapping) -> dict:
    known = profiles()
    out = {}
    for oid, spec in (config or {}).items():
        if not isinstance(spec, Mapping):
            raise PublicTierConfigError(f"{oid}: entry must be a mapping")
        unknown = set(spec) - _KEYS
        if unknown:
            raise PublicTierConfigError(f"{oid}: unknown key(s) {sorted(unknown)}")
        if not isinstance(spec.get("public", False), bool):
            raise PublicTierConfigError(f"{oid}: public must be a boolean")
        if not spec.get("public", False):
            continue
        name = spec.get("limits", "light")
        if name not in known:
            raise PublicTierConfigError(f"{oid}: unknown limits profile {name!r}")
        requires = spec.get("requires")
        if requires not in (None, "key"):
            raise PublicTierConfigError(f"{oid}: requires must be 'key' or absent")
        out[oid] = TierEntry(oid, known[name], requires)
    return out


class PublicTier:
    """A host's parsed public-tier configuration."""

    def __init__(self, config: Mapping | None = None):
        self._configured = dict(config or {})
        self._entries = _parse(self._configured)
        self._warned: set = set()

    @property
    def operation_ids(self) -> tuple:
        return tuple(self._entries)

    def entry(self, op) -> TierEntry | None:
        """The enabled entry of ``op``; ``None`` also when over its ceiling."""
        found = self._entries.get(op.operation_id)
        if found is None:
            return None
        exposure = getattr(op, "exposure", "member")
        if exposure != "public_eligible":
            if op.operation_id not in self._warned:
                self._warned.add(op.operation_id)
                _LOG.error(
                    "[API-K001] %s is in SCITEX_API_PUBLIC_TIER but its exposure "
                    "ceiling is %r; it stays non-public",
                    op.operation_id,
                    exposure,
                )
            return None
        return found

    def status(self, op) -> dict:
        """The tier columns of an operation row (``GET /api/v1/operations``)."""
        if op.public:
            return {"public": True, "reason": None, "limits": "light", "requires": None}
        entry = self.entry(op)
        if entry is None:
            over_ceiling = op.operation_id in self._entries
            return {
                "public": False,
                "reason": "exposure_ceiling" if over_ceiling else None,
                "limits": None,
                "requires": None,
            }
        return {
            "public": True,
            "reason": None,
            "limits": entry.limits.name,
            "requires": entry.requires,
        }


_CACHE: dict = {}


def public_tier() -> PublicTier:
    """The host's tier, parsed once per distinct settings value."""
    config = setting("SCITEX_API_PUBLIC_TIER") or {}
    overrides = setting("SCITEX_API_LIMITS_PROFILES") or {}
    key = repr(
        (
            sorted((k, sorted(dict(v).items())) for k, v in config.items()),
            sorted((k, repr(v)) for k, v in overrides.items()),
        )
    )
    tier = _CACHE.get(key)
    if tier is None:
        _CACHE.clear()
        tier = _CACHE[key] = PublicTier(config)
    return tier


__all__ = ["PublicTier", "PublicTierConfigError", "TierEntry", "public_tier"]
