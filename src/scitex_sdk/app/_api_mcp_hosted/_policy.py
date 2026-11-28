#!/usr/bin/env python3
"""Who sees and calls which hosted tool: scopes and account tiers (API-M002).

A tool is visible to a caller, and callable by it, when BOTH hold:

- the caller's tier reaches the tool's tier (``public`` < ``member`` <
  ``paid``). A public operation's tool is ``public``; any other is
  ``member``. The host may raise a tool's tier (``paid`` for a costly one)
  but never lower it below its declaration;
- the caller's scopes grant the operation's derived scope
  (:func:`~scitex_sdk.app.api_ops.scope_granted`), unless it is public.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..api_exec import ApiCaller, ApiProblem
from ..api_ops import scope_granted

#: Account tiers in rank order (API-Q001 priority classes).
TIERS = ("public", "member", "paid")


class _Anonymous:
    is_authenticated = False
    username = ""
    pk = None


def anonymous_caller() -> ApiCaller:
    """The caller of a request without a credential (public tools only)."""
    return ApiCaller(user=_Anonymous(), scopes=(), via="anonymous", tier="public")


def tier_rank(tier: str) -> int:
    """Rank of ``tier``; an unknown tier ranks lowest (fail closed)."""
    return TIERS.index(tier) if tier in TIERS else 0


def resolve_tiers(specs: Mapping, overrides: Mapping[str, str]) -> dict:
    """Tool name -> tier: the declared default raised by ``overrides``.

    ``overrides`` are keyed by tool name or operation id. An unknown key, an
    unknown tier, or one that would LOWER a tool are configuration errors.
    """
    by_id = {s.operation.operation_id: n for n, s in specs.items()}
    tiers = {
        name: "public" if spec.operation.public else "member"
        for name, spec in specs.items()
    }
    for key, tier in overrides.items():
        name = key if key in specs else by_id.get(key)
        if name is None:
            raise ValueError(f"tool tier for unknown tool {key!r}")
        if tier not in TIERS:
            raise ValueError(f"tier {tier!r} of {key!r} is not one of {TIERS}")
        if tier_rank(tier) < tier_rank(tiers[name]):
            raise ValueError(f"tier {tier!r} would lower {key!r} below {tiers[name]!r}")
        tiers[name] = tier
    return tiers


def denial(caller: ApiCaller, spec, tier: str) -> ApiProblem | None:
    """Why ``caller`` may not use ``spec`` (a problem), or ``None``.

    The host's public tier (``SCITEX_API_PUBLIC_TIER``, contract §12) opens an
    operation to anonymous callers (``anonymous_allowed``) and to every key
    whatever its account tier, exactly as on REST; the scope check still
    applies to keys.
    """
    from ..api_tier import anonymous_allowed, public_tier

    op = spec.operation
    if caller.via == "anonymous" and not op.public:
        allowed, entry = anonymous_allowed(op)
        if allowed:
            return None
        if entry is not None:
            return ApiProblem(
                401,
                "api.key_required",
                "this tool is free to call with any SciTeX API key, but not "
                "anonymously; send one as Authorization: Bearer",
            )
    in_public_tier = public_tier().entry(op) is not None
    if not in_public_tier and tier_rank(caller.tier) < tier_rank(tier):
        return ApiProblem(
            403,
            "api.tier_required",
            f"this tool needs the {tier} tier",
            extra={"required_tier": tier},
        )
    if not op.public and not scope_granted(op.scope, caller.scopes):
        return ApiProblem(
            403,
            "api.insufficient_scope",
            f"this operation needs the scope {op.scope}",
            extra={"required_scope": op.scope},
        )
    return None


__all__ = ["TIERS", "anonymous_caller", "denial", "resolve_tiers", "tier_rank"]
