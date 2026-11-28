#!/usr/bin/env python3
"""Concurrency slots per priority class (API-Q002/Q003) and rate buckets (API-H002).

Both keep their counters in the host's Django cache (``SCITEX_API_TIER_CACHE``,
default ``"default"``; Redis in production), so they hold across workers. Every
counter has a TTL, so a crashed worker cannot hold a slot or a window forever.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from contextlib import contextmanager

from ._decision import TierDecision, decide
from ._profiles import setting

DEFAULT_POOL_SLOTS = 8
#: The share of a pool's slots each class may hold at most. ``paid`` may use
#: every slot; the rest never exceed 40 %, so >= 60 % stays reserved for paid
#: work even when idle (API-Q003); ``public`` is capped at 20 %.
CLASS_SHARE = {"paid": 1.0, "member": 0.4, "public": 0.2}
DEFAULT_RATE_BUCKETS = {
    "public": {"per_minute": 30, "per_day": 1000},
    "member": {"per_minute": 120, "per_day": 10000},
    "paid": {"per_minute": 600, "per_day": None},
}


def _problem(*args, **kwargs):
    from ..api_exec import ApiProblem

    return ApiProblem(*args, **kwargs)


def _cache():
    from django.core.cache import caches

    return caches[setting("SCITEX_API_TIER_CACHE", "default")]


def _incr(cache, key: str, ttl: int) -> int:
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.add(key, 0, ttl)
        return cache.incr(key)


def class_limit(pool_slots: int, klass: str) -> int:
    """Slots of a ``pool_slots``-slot pool that ``klass`` may hold (>= 1)."""
    if klass == "paid":
        return pool_slots
    return max(
        1, math.floor(pool_slots * CLASS_SHARE.get(klass, CLASS_SHARE["public"]))
    )


class SlotPools:
    """Concurrency slots per pool, shared by class.

    A synchronous call of an operation enabled in the public tier holds one
    slot of the pool named after its limits profile while it runs. Pool sizes
    come from ``SCITEX_API_POOLS`` (default :data:`DEFAULT_POOL_SLOTS`). A full
    pool for the caller's class is a 503 ``api.capacity_deferred`` with
    ``Retry-After`` (API-Q002) — never a silent stall.
    """

    def __init__(self, sizes: Mapping | None = None):
        self.sizes = dict(sizes or {})

    @classmethod
    def from_settings(cls) -> SlotPools:
        return cls(setting("SCITEX_API_POOLS") or {})

    def size(self, pool: str) -> int:
        return int(self.sizes.get(pool, DEFAULT_POOL_SLOTS))

    @contextmanager
    def slot(self, pool: str, klass: str, ttl: int = 120):
        cache = _cache()
        keys = (f"scitex-api-slot:{pool}:total", f"scitex-api-slot:{pool}:{klass}")
        size = self.size(pool)
        held_total = _incr(cache, keys[0], ttl)
        held_class = _incr(cache, keys[1], ttl)
        try:
            if held_total > size or held_class > class_limit(size, klass):
                raise _problem(
                    503,
                    "api.capacity_deferred",
                    f"the {pool} pool is full for the {klass} priority class; "
                    "retry after the interval in Retry-After",
                    retryable=True,
                    headers={"Retry-After": "5"},
                    extra={"priority_class": klass},
                )
            yield
        finally:
            for key in keys:
                try:
                    cache.decr(key)
                except ValueError:  # expired: nothing left to release
                    pass


class TierRateLimiter:
    """A ``SCITEX_API_RATE_LIMITER`` with per-class buckets (§12.3).

    Fixed windows per minute and per day, per rate key (the token for keys, the
    client IP /64 for anonymous callers), with limits per priority class from
    ``SCITEX_API_RATE_BUCKETS`` over :data:`DEFAULT_RATE_BUCKETS`. A refusal is
    429 ``api.rate_limited`` with ``Retry-After``, ``RateLimit-Policy`` and
    ``RateLimit`` (API-H002).
    """

    def __init__(self, buckets: Mapping | None = None):
        configured = (
            buckets if buckets is not None else setting("SCITEX_API_RATE_BUCKETS")
        )
        self.buckets = {**DEFAULT_RATE_BUCKETS, **dict(configured or {})}

    def check(self, caller, operation, request, decision: TierDecision | None = None):
        decision = decision or decide(operation, caller, request)
        bucket = self.buckets.get(decision.priority_class) or {}
        now = time.time()
        cache = _cache()
        for name, seconds in (("per_minute", 60), ("per_day", 86400)):
            limit = bucket.get(name)
            if not limit:
                continue
            window = int(now // seconds)
            key = f"scitex-api-rate:{decision.rate_key}:{name}:{window}"
            if _incr(cache, key, seconds + 5) <= int(limit):
                continue
            retry = int((window + 1) * seconds - now) + 1
            raise _problem(
                429,
                "api.rate_limited",
                f"the {decision.priority_class} rate limit is {limit} calls "
                f"{name.replace('_', ' ')}",
                retryable=True,
                headers={
                    "Retry-After": str(retry),
                    "RateLimit-Policy": f'"{name}";q={limit};w={seconds}',
                    "RateLimit": f'"{name}";r=0;t={retry}',
                },
                extra={"priority_class": decision.priority_class},
            )


__all__ = [
    "CLASS_SHARE",
    "DEFAULT_POOL_SLOTS",
    "DEFAULT_RATE_BUCKETS",
    "SlotPools",
    "TierRateLimiter",
    "class_limit",
]
