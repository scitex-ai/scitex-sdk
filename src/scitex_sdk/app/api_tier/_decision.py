#!/usr/bin/env python3
"""Classify one call: priority class, sponsorship, limits, rate key (§12.2-12.3)."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from ._config import PublicTier, TierEntry, public_tier
from ._profiles import (
    PRIORITY_CLASSES,
    SPONSORED_USAGE_KIND,
    LimitsProfile,
    profile_for,
    setting,
)


def priority_class(caller) -> str:
    """API-Q001: the class of the caller the HOST resolved, never a parameter.

    An anonymous caller is ``public``; otherwise ``caller.tier`` as the host
    assigned it (``paid`` for an active paid plan, ``member`` for a trial or
    unpaid key, ``public`` for a low-trust key). Anything else is ``member``.
    """
    if caller is None or getattr(caller, "via", "") == "anonymous":
        return "public"
    tier = getattr(caller, "tier", "member")
    return tier if tier in PRIORITY_CLASSES else "member"


def client_key(request) -> str:
    """The anonymous rate key of ``request``: the client IP, IPv6 as its /64.

    The address comes from ``SCITEX_API_CLIENT_IP`` (``client_ip(request)``)
    when the host sets one (behind a proxy), else from ``REMOTE_ADDR``.
    """
    hook = setting("SCITEX_API_CLIENT_IP")
    if hook is not None:
        if isinstance(hook, str):
            from django.utils.module_loading import import_string

            hook = import_string(hook)
        raw = hook(request)
    else:
        raw = (getattr(request, "META", None) or {}).get("REMOTE_ADDR", "")
    try:
        address = ipaddress.ip_address(str(raw or "").strip())
    except ValueError:
        return "ip:unknown"
    if address.version == 6:
        if address.ipv4_mapped is not None:
            return f"ip:{address.ipv4_mapped}"
        return "ip:" + str(ipaddress.ip_network(f"{address}/64", strict=False))
    return f"ip:{address}"


@dataclass(frozen=True)
class TierDecision:
    """How one call is classed, limited and rated."""

    priority_class: str
    #: The public-tier entry when the operation is enabled there.
    entry: TierEntry | None
    #: Rated to the SciTeX promotion account (API-K005).
    sponsored: bool
    #: The profile this call is measured against (API-K003).
    limits: LimitsProfile | None
    #: Token for keys, client IP (/64) for anonymous callers.
    rate_key: str

    @property
    def payer(self) -> str:
        return "promotion" if self.sponsored else "caller"

    @property
    def enforced_limits(self) -> LimitsProfile | None:
        """What a handler must enforce: the public profile, for the public class.

        Members and paid callers get the operation's normal limits (§12.4).
        """
        if self.entry is not None and self.priority_class == "public":
            return self.entry.limits
        return None

    def as_meter_fields(self) -> dict:
        return {
            "priority_class": self.priority_class,
            "sponsored": self.sponsored,
            "payer": self.payer,
            "usage_kind": SPONSORED_USAGE_KIND if self.sponsored else None,
            "limits_profile": self.limits.name if self.limits else None,
        }


def anonymous_allowed(op, tier: PublicTier | None = None) -> tuple:
    """``(allowed, entry)`` for an anonymous call of ``op`` (API-A004)."""
    if op.public:
        return True, None
    entry = (tier or public_tier()).entry(op)
    if entry is None or entry.requires == "key":
        return False, entry
    return True, entry


def _rate_key(caller, request) -> str:
    if getattr(caller, "via", "") == "anonymous":
        if caller.token_id:
            return caller.token_id
        return client_key(request) if request is not None else "ip:unknown"
    user = getattr(caller, "user", None)
    ident = getattr(caller, "token_id", None) or getattr(user, "pk", None) or ""
    return f"{getattr(caller, 'via', 'token')}:{ident}"


def decide(op, caller, request=None, tier: PublicTier | None = None) -> TierDecision:
    """Class, sponsorship and limits of ``caller`` calling ``op``.

    A call of an operation enabled in the public tier is sponsored unless the
    caller is ``paid`` (a paying member's call is rated to that member).
    """
    entry = (tier or public_tier()).entry(op)
    klass = priority_class(caller)
    limits = entry.limits if entry is not None else profile_for(op)
    return TierDecision(
        priority_class=klass,
        entry=entry,
        sponsored=entry is not None and klass != "paid",
        limits=limits,
        rate_key=_rate_key(caller, request),
    )


__all__ = [
    "TierDecision",
    "anonymous_allowed",
    "client_key",
    "decide",
    "priority_class",
]
