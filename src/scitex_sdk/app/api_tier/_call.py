#!/usr/bin/env python3
"""One tiered call, transport-neutral: the part REST and hosted MCP share.

:func:`run_tiered` wraps a call of :func:`~scitex_sdk.app.api_exec.execute`:

1. classify it (:func:`~._decision.decide`);
2. ask the host's admission hook (``SCITEX_API_ADMISSION.admit``): the host's
   credit gate for a call rated to the caller, and its promotion-budget check
   for a sponsored call (API-K005..K007). It may refuse (raise ``ApiProblem``,
   e.g. 402 insufficient credit) or return a replacement :class:`TierDecision`
   (a degraded priority class once the promotion budget is spent); in shadow
   mode it records and returns ``None``;
3. refuse a public-class request larger than its profile (413);
4. hold a slot of the profile's pool for a synchronous call (API-Q003);
5. measure the call and flag usage above its class (API-K003).

The caller of :func:`run_tiered` adds ``SciTeX-Priority-Class`` to the answer
and the returned meter fields to its meter event (API-Q002, API-H004).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ._capacity import SlotPools
from ._decision import TierDecision, anonymous_allowed, client_key, decide
from ._measure import Measurement, measured
from ._profiles import setting

PRIORITY_HEADER = "SciTeX-Priority-Class"


class _Anonymous:
    is_authenticated = False
    username = ""
    pk = None


ANONYMOUS_USER = _Anonymous()


def anonymous_caller(op, request):
    """The caller of a request WITHOUT a credential, or ``None`` (-> 401).

    API-A004: an always-public read (``public=True``) and an operation the
    host's public tier enables for anonymous callers (API-K008, within the
    ``public_eligible`` ceiling) run as the anonymous ``public`` class. For a
    tier operation the host grants exactly that operation's scope. The caller
    is keyed by its client IP, so the idempotency keys and rate buckets of
    different anonymous clients never mix. A tier operation that requires a
    key raises a 401 ``api.key_required`` saying so.

    Only for a request that presented NO credential: one that presented an
    invalid credential stays a 401 (API-A002).
    """
    from ..api_exec import ApiCaller, ApiProblem

    allowed, entry = anonymous_allowed(op)
    if allowed:
        return ApiCaller(
            user=ANONYMOUS_USER,
            scopes=() if op.public else (op.scope,),
            via="anonymous",
            token_id=client_key(request),
            tier="public",
        )
    if entry is not None:
        raise ApiProblem(
            401,
            "api.key_required",
            "this operation is free to call with any SciTeX API key, but not "
            "anonymously; create a key and send it as Authorization: Bearer",
            headers={"WWW-Authenticate": 'Bearer realm="scitex"'},
        )
    return None


def _hook(name: str):
    value = setting(name)
    if value is None:
        return None
    if isinstance(value, str):
        from django.utils.module_loading import import_string

        value = import_string(value)
    return value() if isinstance(value, type) else value


@dataclass
class TieredCall:
    """The outcome of :func:`run_tiered` besides the result itself."""

    decision: TierDecision
    measurement: Measurement | None = None

    def meter_fields(self, response_bytes: int) -> dict:
        fields = self.decision.as_meter_fields()
        if self.measurement is not None:
            fields.update(self.measurement.as_meter_fields())
            fields["cost_class_exceeded"] = self.measurement.exceeded(
                self.decision.limits, response_bytes
            )
        else:
            fields["cost_class_exceeded"] = []
        return fields

    @property
    def headers(self) -> dict:
        return {PRIORITY_HEADER: self.decision.priority_class}


def check_request_size(decision: TierDecision, request_bytes: int) -> None:
    """413 ``api.request_too_large`` above the public profile's input cap."""
    limits = decision.enforced_limits
    cap = limits.max_request_bytes if limits is not None else None
    if cap is not None and request_bytes > cap:
        from ..api_exec import ApiProblem

        raise ApiProblem(
            413,
            "api.request_too_large",
            f"the request is {request_bytes} bytes; the {limits.name} limit for "
            f"public calls is {cap} bytes (an API key lifts it)",
            extra={"limit": "max_request_bytes", "max_request_bytes": cap},
        )


def run_tiered(
    op,
    caller,
    request,
    run: Callable[[TierDecision], object],
    *,
    request_bytes: int = 0,
    tiered: TieredCall | None = None,
):
    """``(run(decision), TieredCall)``; a refusal raises ``ApiProblem``.

    ``tiered`` lets a transport keep the classification even when this raises
    (the meter still records the class of a refused call).
    """
    tiered = tiered or TieredCall(decide(op, caller, request))
    admission = _hook("SCITEX_API_ADMISSION")
    if admission is not None:
        replaced = admission.admit(tiered.decision, op, caller, request)
        if isinstance(replaced, TierDecision):
            tiered.decision = replaced
    decision = tiered.decision
    check_request_size(decision, request_bytes)
    hold_slot = decision.entry is not None and not decision.entry.limits.asynchronous
    with measured() as measurement:
        tiered.measurement = measurement
        if hold_slot:
            pool = decision.entry.limits.name
            ttl = int((decision.entry.limits.wall_seconds or 60) * 2) + 5
            with SlotPools.from_settings().slot(pool, decision.priority_class, ttl):
                result = run(decision)
        else:
            result = run(decision)
    return result, tiered


__all__ = [
    "ANONYMOUS_USER",
    "PRIORITY_HEADER",
    "TieredCall",
    "anonymous_caller",
    "check_request_size",
    "run_tiered",
]
