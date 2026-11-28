#!/usr/bin/env python3
"""Per-call measurement and the ``cost_class_exceeded`` flags (API-K002/K003).

``execute`` is wrapped in :func:`measured`: wall time (``perf_counter``) and
thread CPU time (``thread_time``) on every call, peak memory with
:mod:`tracemalloc` on a sample of calls (``SCITEX_API_MEMORY_SAMPLE_RATE``,
default 1 %). The storage-write and external-call flags are exact: a handler
can do either only through a ``scitex_sdk.host`` capability, and the
capability calls :func:`flag_call`.
"""

from __future__ import annotations

import contextvars
import random
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field

from ._profiles import EXCEEDED_FLAGS, LimitsProfile, setting

DEFAULT_MEMORY_SAMPLE_RATE = 0.01
_EXACT_FLAGS = ("storage_write", "external")
_FLAGS: contextvars.ContextVar = contextvars.ContextVar("scitex_api_call_flags")


def flag_call(name: str) -> None:
    """Mark the running call (``storage_write`` or ``external``).

    A no-op outside a measured call, so a capability can call it unconditionally.
    """
    if name not in _EXACT_FLAGS:
        raise ValueError(f"unknown call flag {name!r}; one of {_EXACT_FLAGS}")
    flags = _FLAGS.get(None)
    if flags is not None:
        flags.add(name)


@dataclass
class Measurement:
    """What one call used."""

    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    peak_memory_bytes: int | None = None
    flags: set = field(default_factory=set)

    def exceeded(self, limits: LimitsProfile | None, response_bytes: int) -> list:
        """API-K003: the flags of this call against ``limits``, in report order."""
        out = {f for f in self.flags if f in _EXACT_FLAGS}
        if limits is not None:
            checks = (
                ("cpu", limits.cpu_seconds, self.cpu_seconds),
                ("wall", limits.wall_seconds, self.wall_seconds),
                ("memory", limits.memory_bytes, self.peak_memory_bytes),
                ("bytes", limits.max_response_bytes, response_bytes),
            )
            for flag, bound, used in checks:
                if bound is not None and used is not None and used > bound:
                    out.add(flag)
        return [f for f in EXCEEDED_FLAGS if f in out]

    def as_meter_fields(self) -> dict:
        return {
            "wall_seconds": round(self.wall_seconds, 6),
            "cpu_seconds": round(self.cpu_seconds, 6),
            "peak_memory_bytes": self.peak_memory_bytes,
        }


def _sample_rate(explicit: float | None) -> float:
    if explicit is not None:
        return float(explicit)
    return float(setting("SCITEX_API_MEMORY_SAMPLE_RATE", DEFAULT_MEMORY_SAMPLE_RATE))


@contextmanager
def measured(sample_rate: float | None = None):
    """Measure the enclosed call; yields the :class:`Measurement` it fills."""
    rate = _sample_rate(sample_rate)
    sample = rate > 0 and random.random() < rate and not tracemalloc.is_tracing()
    result = Measurement()
    token = _FLAGS.set(result.flags)
    if sample:
        tracemalloc.start()
    started_wall = time.perf_counter()
    started_cpu = time.thread_time()
    try:
        yield result
    finally:
        result.cpu_seconds = time.thread_time() - started_cpu
        result.wall_seconds = time.perf_counter() - started_wall
        if sample:
            result.peak_memory_bytes = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
        _FLAGS.reset(token)


__all__ = ["DEFAULT_MEMORY_SAMPLE_RATE", "Measurement", "flag_call", "measured"]
