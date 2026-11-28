#!/usr/bin/env python3
"""API-K004: run every ``public_eligible`` operation on its example inputs.

A leaf passes example inputs per operation id; each example is served through
the real SDK host path as an ANONYMOUS ``public``-class call, with the
operation enabled in a public tier under ``limits`` (the profile the host will
use), and must answer 2xx without any ``cost_class_exceeded`` flag::

    from scitex_sdk.testing.api_examples import assert_examples_within_limits

    def test_public_examples_stay_light():
        assert_examples_within_limits(
            PLUGIN,
            {"stats.tests.run": {"limits": "stats-inline", "id": "ttest_ind",
                                 "params": {"data": [1, 2, 3], "data2": [2, 3, 4]}}},
        )

Unlike the served contract suite, this RUNS the handlers, so examples must be
side-effect free beyond the leaf's own ephemeral state.
"""

from __future__ import annotations

import json
import types
import uuid

from scitex_sdk.app.api_ops import operations
from scitex_sdk.app.api_plugin import ApiPlugin

from .api_contract import Violation, _ensure_django, _ref_for


class _Meter:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


def _url(op, item_id):
    path = op.path
    if op.id_param:
        path = path.replace("{" + op.id_param + "}", str(item_id))
    return f"/api/v1/{op.package}/{path}"


def run_examples(plugin: ApiPlugin, examples: dict, *, target: str | None = None):
    """Violations of API-K004 for ``examples`` (``{operation_id: example}``).

    An example is ``{"params": {...}, "id": item_id?, "limits": profile?}``.
    """
    _ensure_django()
    from django.test import Client, override_settings

    from scitex_sdk.app.api_serve import InMemoryIdempotencyStore, api_urlpatterns

    ops = {op.operation_id: op for op in operations(plugin)}
    out = []
    for oid in examples:
        if oid not in ops:
            out.append(
                Violation("API-K004", oid, "example for an undeclared operation")
            )
        elif ops[oid].exposure != "public_eligible":
            out.append(
                Violation(
                    "API-K004", oid, "example for a non-public_eligible operation"
                )
            )
    for oid, op in ops.items():
        if op.exposure == "public_eligible" and not op.public and oid not in examples:
            out.append(
                Violation("API-K004", oid, "public_eligible operation has no example")
            )
    urlconf = types.ModuleType("scitex_sdk_api_examples_urls")
    urlconf.urlpatterns = api_urlpatterns([_ref_for(plugin, target)])
    tier = {
        oid: {"public": True, "limits": ex.get("limits", "light")}
        for oid, ex in examples.items()
        if oid in ops
    }
    meter = _Meter()
    with override_settings(
        ROOT_URLCONF=urlconf,
        SCITEX_API_CALLER=lambda request: None,
        SCITEX_API_IDEMPOTENCY_STORE=InMemoryIdempotencyStore(),
        SCITEX_API_RATE_LIMITER=None,
        SCITEX_API_METER=meter,
        SCITEX_API_PUBLIC_TIER=tier,
        SCITEX_API_MEMORY_SAMPLE_RATE=1.0,
    ):
        client = Client()
        for oid, example in examples.items():
            op = ops.get(oid)
            if op is None:
                continue
            url = _url(op, example.get("id", "example"))
            headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
            if op.method == "GET":
                response = client.get(url, example.get("params", {}), **headers)
            else:
                response = client.generic(
                    op.method,
                    url,
                    json.dumps(example.get("params", {})),
                    content_type="application/json",
                    **headers,
                )
            if not 200 <= response.status_code < 300:
                out.append(
                    Violation(
                        "API-K004",
                        oid,
                        f"example answered {response.status_code}: "
                        f"{response.content[:300]!r}",
                    )
                )
                continue
            event = meter.events[-1] if meter.events else {}
            flags = event.get("cost_class_exceeded") or []
            if flags:
                out.append(
                    Violation(
                        "API-K004",
                        oid,
                        f"example exceeds its {event.get('limits_profile')} profile: "
                        f"{flags} (cpu {event.get('cpu_seconds')} s, wall "
                        f"{event.get('wall_seconds')} s, peak memory "
                        f"{event.get('peak_memory_bytes')} B)",
                    )
                )
    return out


def assert_examples_within_limits(
    plugin: ApiPlugin, examples: dict, *, target: str | None = None
) -> None:
    """Fail with every API-K004 violation of ``plugin``'s examples."""
    found = run_examples(plugin, examples, target=target)
    if found:
        lines = "\n".join(f"  {v}" for v in found)
        raise AssertionError(
            f"API-K004 violations in plugin {plugin.id!r} ({len(found)}):\n{lines}"
        )


__all__ = ["assert_examples_within_limits", "run_examples"]
