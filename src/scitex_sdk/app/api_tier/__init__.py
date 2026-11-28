#!/usr/bin/env python3
"""Cost class, exposure ceiling, priority classes and the public tier (contract §12).

The DECLARATION (code, part of the contract) says what an operation *is*:
``compute_cost`` and ``exposure`` on :class:`~scitex_sdk.app.api_ops.ApiOperation`.
The public-tier CONFIGURATION (host settings, not contract) says who may call
it for free today. This package is the host-side half. :mod:`..api_serve` (REST)
uses it, and any other transport (hosted MCP) calls :func:`run_tiered` so every
transport applies the same rules.

Host settings (all optional; nothing is public until the host says so):

``SCITEX_API_PUBLIC_TIER`` (API-K008)
    ``{operation_id: {"public": True, "limits": profile, "requires": "key"}}``.
    The only switch; it can narrow, never widen past ``exposure`` (API-K001).
``SCITEX_API_LIMITS_PROFILES``
    overrides of :data:`PROFILES` by name.
``SCITEX_API_POOLS``
    ``{pool: slots}`` for synchronous tiered calls (pool = profile name).
``SCITEX_API_RATE_BUCKETS``
    per-class ``{"per_minute": n, "per_day": n}`` for :class:`TierRateLimiter`.
``SCITEX_API_ADMISSION``
    ``admit(decision, op, caller, request) -> TierDecision | None``: the host's
    credit gate (calls rated to the caller) and promotion-budget check
    (sponsored calls). Raise ``ApiProblem`` to refuse; return a replacement
    decision to degrade the priority class; return ``None`` to admit as is.
``SCITEX_API_CLIENT_IP``
    ``client_ip(request) -> str`` behind a proxy (default ``REMOTE_ADDR``).
``SCITEX_API_MEMORY_SAMPLE_RATE``
    fraction of calls whose peak memory is sampled (default 0.01).

Priority classes (API-Q001): ``paid`` > ``member`` > ``public``, from
``ApiCaller.tier`` as the host assigned it; an anonymous caller is ``public``.
"""

from ._call import (
    ANONYMOUS_USER,
    PRIORITY_HEADER,
    TieredCall,
    anonymous_caller,
    check_request_size,
    run_tiered,
)
from ._capacity import (
    CLASS_SHARE,
    DEFAULT_POOL_SLOTS,
    DEFAULT_RATE_BUCKETS,
    SlotPools,
    TierRateLimiter,
    class_limit,
)
from ._config import PublicTier, PublicTierConfigError, TierEntry, public_tier
from ._decision import (
    TierDecision,
    anonymous_allowed,
    client_key,
    decide,
    priority_class,
)
from ._measure import DEFAULT_MEMORY_SAMPLE_RATE, Measurement, flag_call, measured
from ._profiles import (
    EXCEEDED_FLAGS,
    EXPOSURES,
    PRIORITY_CLASSES,
    PROFILES,
    SPONSORED_USAGE_KIND,
    LimitsProfile,
    profile_for,
    profiles,
)

__all__ = [
    "ANONYMOUS_USER",
    "CLASS_SHARE",
    "DEFAULT_MEMORY_SAMPLE_RATE",
    "DEFAULT_POOL_SLOTS",
    "DEFAULT_RATE_BUCKETS",
    "EXCEEDED_FLAGS",
    "EXPOSURES",
    "PRIORITY_CLASSES",
    "PRIORITY_HEADER",
    "PROFILES",
    "SPONSORED_USAGE_KIND",
    "LimitsProfile",
    "Measurement",
    "PublicTier",
    "PublicTierConfigError",
    "SlotPools",
    "TierDecision",
    "TierEntry",
    "TierRateLimiter",
    "TieredCall",
    "anonymous_allowed",
    "anonymous_caller",
    "check_request_size",
    "class_limit",
    "client_key",
    "decide",
    "flag_call",
    "measured",
    "priority_class",
    "profile_for",
    "profiles",
    "public_tier",
    "run_tiered",
]
