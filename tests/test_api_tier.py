"""Public light compute tier (contract §12): exposure, classes, limits, metering."""

import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
from django.core.cache import caches
from django.test import Client, override_settings

from scitex_sdk.app.api_ops import ApiOperation
from scitex_sdk.app.api_rules import ApiContractViolation
from scitex_sdk.app.api_tier import (
    PublicTier,
    PublicTierConfigError,
    SlotPools,
    class_limit,
    client_key,
    flag_call,
    measured,
)
from tests import _api_ops_tier as leaf

HOOKS = dict(
    ROOT_URLCONF="tests._api_ops_tier",
    SCITEX_API_CALLER="tests._api_ops_tier.caller",
    SCITEX_API_METER=leaf.Meter(),
    SCITEX_API_ADMISSION=leaf.Admission(),
    SCITEX_API_PUBLIC_TIER=leaf.TIER,
    SCITEX_API_IDEMPOTENCY_STORE="scitex_sdk.app.api_serve.InMemoryIdempotencyStore",
    SCITEX_API_RATE_LIMITER="scitex_sdk.app.api_tier.TierRateLimiter",
    SCITEX_API_RATE_BUCKETS={"public": {"per_minute": 5, "per_day": 100}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@pytest.fixture(autouse=True)
def _clean():
    leaf.METERED.clear()
    leaf.SEEN.clear()
    leaf.Admission.calls.clear()
    with override_settings(**HOOKS):
        caches["default"].clear()
        yield


def _rule_of(build):
    try:
        build()
    except ApiContractViolation as exc:
        return exc.rule
    return None


def _post(path, body, token=None, key="k1", ip="203.0.113.7"):
    headers = {"REMOTE_ADDR": ip}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if key:
        headers["HTTP_IDEMPOTENCY_KEY"] = key
    return Client().post(
        path, json.dumps(body), content_type="application/json", **headers
    )


# ------------------------------------------------------------- declaration


def test_exposure_defaults_to_member():
    # Arrange
    # Act
    op = ApiOperation("calc", "things", "create", "m:f")
    # Assert
    assert op.exposure == "member"


def test_a_public_operation_is_public_eligible():
    # Arrange
    # Act
    op = ApiOperation("calc", "things", "list", "m:f", paginated=True, public=True)
    # Assert
    assert op.exposure == "public_eligible"


def test_a_project_scoped_operation_cannot_be_public_eligible():
    # Arrange
    kwargs = dict(project_scoped=True, exposure="public_eligible")
    # Act
    rule = _rule_of(lambda: ApiOperation("calc", "things", "create", "m:f", **kwargs))
    # Assert
    assert rule == "API-K001"


def test_an_unknown_exposure_is_refused():
    # Arrange
    kwargs = dict(exposure="free")
    # Act
    rule = _rule_of(lambda: ApiOperation("calc", "things", "create", "m:f", **kwargs))
    # Assert
    assert rule == "API-K001"


def test_exposure_survives_the_route_round_trip():
    # Arrange
    from scitex_sdk.app.api_ops import operations

    # Act
    exposures = {op.operation_id: op.exposure for op in operations(leaf.PLUGIN)}
    # Assert
    assert exposures["calc.sums.run"] == "public_eligible"


def test_exposure_is_in_the_openapi_fragment():
    # Arrange
    fragment = leaf.PLUGIN.openapi_fragment()
    # Act
    found = {
        op["operationId"]: op["x-scitex-exposure"]
        for item in fragment["paths"].values()
        for op in item.values()
        if isinstance(op, dict) and "operationId" in op
    }
    # Assert
    assert set(found.values()) == {"public_eligible", "member"}


def test_a_malformed_tier_config_is_refused():
    # Arrange
    config = {"calc.sums.run": {"public": True, "limits": "no-such"}}
    # Act
    try:
        PublicTier(config)
        refused = False
    except PublicTierConfigError:
        refused = True
    # Assert
    assert refused


def test_the_tier_cannot_widen_past_the_ceiling():
    # Arrange
    tier = PublicTier(leaf.TIER)
    note = next(o for o in leaf.OPERATIONS if o.resource == "notes")
    # Act
    status = tier.status(note)
    # Assert
    assert status == {
        "public": False,
        "reason": "exposure_ceiling",
        "limits": None,
        "requires": None,
    }


# ------------------------------------------------------------- serving


def test_an_anonymous_caller_runs_a_tier_operation_as_public():
    # Arrange
    # Act
    response = _post("/api/v1/calc/sums/run", {"values": [1, 2, 3]}, key=None)
    # Assert
    assert (
        response.status_code,
        response.json()["data"],
        response["SciTeX-Priority-Class"],
    ) == (
        200,
        {"total": 6, "class": "public"},
        "public",
    )


def test_the_public_class_gets_the_profile_limits():
    # Arrange
    values = list(range(100_001))
    # Act
    response = _post("/api/v1/calc/sums/run", {"values": values}, key=None)
    # Assert
    assert response.json()["code"] == "calc.too_many_values"


def test_a_member_key_lifts_the_public_limits():
    # Arrange
    values = list(range(100_001))
    # Act
    response = _post("/api/v1/calc/sums/run", {"values": values}, token="member-key")
    # Assert
    assert response.json()["data"]["class"] == "member"


def test_anonymous_is_refused_where_the_tier_requires_a_key():
    # Arrange
    # Act
    response = _post("/api/v1/calc/renders", {"values": [1]})
    # Assert
    assert (response.status_code, response.json()["code"]) == (401, "api.key_required")


def test_any_key_may_call_a_key_only_tier_operation():
    # Arrange
    # Act
    response = _post("/api/v1/calc/renders", {"values": [1]}, token="member-key")
    # Assert
    assert response.status_code == 201


def test_an_operation_over_its_ceiling_stays_closed_to_anonymous():
    # Arrange
    # Act
    response = _post("/api/v1/calc/notes", {"values": [1]})
    # Assert
    assert response.status_code == 401


def test_an_invalid_bearer_never_falls_back_to_anonymous():
    # Arrange
    # Act
    response = _post("/api/v1/calc/sums/run", {"values": [1]}, token="bogus")
    # Assert
    assert response.status_code == 401


def test_the_meter_records_class_sponsorship_and_usage():
    # Arrange
    # Act
    _post("/api/v1/calc/sums/run", {"values": [1]}, key=None)
    # Assert
    event = leaf.METERED[-1]
    assert {
        k: event[k] for k in ("priority_class", "sponsored", "payer", "usage_kind")
    } == {
        "priority_class": "public",
        "sponsored": True,
        "payer": "promotion",
        "usage_kind": "public_compute",
    }


def test_a_paid_call_is_rated_to_the_caller():
    # Arrange
    # Act
    _post("/api/v1/calc/sums/run", {"values": [1]}, token="paid-key")
    # Assert
    event = leaf.METERED[-1]
    assert (event["priority_class"], event["payer"], event["user_id"]) == (
        "paid",
        "caller",
        "paid-key",
    )


def test_the_meter_carries_measured_cpu_and_wall():
    # Arrange
    # Act
    _post("/api/v1/calc/sums/run", {"values": [1]}, key=None)
    # Assert
    event = leaf.METERED[-1]
    assert (
        event["wall_seconds"] >= event["cpu_seconds"] >= 0
        and event["cost_class_exceeded"] == []
    )


def test_the_admission_hook_sees_every_call():
    # Arrange
    # Act
    _post("/api/v1/calc/sums/run", {"values": [1]}, key=None)
    # Assert
    assert leaf.Admission.calls == [("public", "calc.sums.run")]


def test_the_admission_hook_can_degrade_the_class():
    # Arrange
    import dataclasses

    class Degrade:
        def admit(self, decision, op, caller, request):
            return dataclasses.replace(decision, priority_class="public")

    # Act
    with override_settings(SCITEX_API_ADMISSION=Degrade()):
        response = _post("/api/v1/calc/sums/run", {"values": [1]}, token="member-key")
    # Assert
    assert response["SciTeX-Priority-Class"] == "public"


def test_public_callers_are_rate_limited_per_ip():
    # Arrange
    for _ in range(5):
        _post("/api/v1/calc/sums/run", {"values": [1]}, key=None)
    # Act
    limited = _post("/api/v1/calc/sums/run", {"values": [1]}, key=None)
    other_ip = _post(
        "/api/v1/calc/sums/run", {"values": [1]}, key=None, ip="198.51.100.1"
    )
    # Assert
    assert (
        limited.status_code,
        limited["Retry-After"] != "",
        other_ip.status_code,
    ) == (
        429,
        True,
        200,
    )


def test_an_oversized_public_request_is_a_413():
    # Arrange
    with override_settings(
        SCITEX_API_LIMITS_PROFILES={"stats-inline": {"max_request_bytes": 64}}
    ):
        # Act
        response = _post(
            "/api/v1/calc/sums/run", {"values": list(range(100))}, key=None
        )
    # Assert
    assert (response.status_code, response.json()["code"]) == (
        413,
        "api.request_too_large",
    )


def test_anonymous_idempotency_keys_do_not_mix_across_clients():
    # Arrange
    tier = {**leaf.TIER, "calc.renders.create": {"public": True, "limits": "light"}}
    with override_settings(SCITEX_API_PUBLIC_TIER=tier):
        _post("/api/v1/calc/renders", {"values": [1]}, key="same")
        # Act
        other = _post(
            "/api/v1/calc/renders",
            {"values": [2]},
            key="same",
            ip="198.51.100.9",
        )
    # Assert
    assert other.status_code == 201 and "Idempotent-Replayed" not in other


# ------------------------------------------------------------- pieces


def test_ipv6_clients_are_aggregated_to_their_64():
    # Arrange
    a = type("R", (), {"META": {"REMOTE_ADDR": "2001:db8:1:2::1"}})()
    b = type("R", (), {"META": {"REMOTE_ADDR": "2001:db8:1:2:ffff::9"}})()
    # Act
    # Assert
    assert client_key(a) == client_key(b) == "ip:2001:db8:1:2::/64"


def test_paid_reserves_sixty_percent_of_a_pool():
    # Arrange
    # Act
    limits = {k: class_limit(10, k) for k in ("paid", "member", "public")}
    # Assert
    assert limits == {"paid": 10, "member": 4, "public": 2}


def test_a_full_pool_defers_the_public_class():
    # Arrange
    from scitex_sdk.app.api_exec import ApiProblem

    pools = SlotPools({"p": 5})
    # Act
    with pools.slot("p", "public"):
        try:
            with pools.slot("p", "public"):
                code = None
        except ApiProblem as exc:
            code = exc.code
        with pools.slot("p", "paid"):
            paid_ok = True
    # Assert
    assert (code, paid_ok) == ("api.capacity_deferred", True)


def test_a_storage_write_is_flagged_exactly():
    # Arrange
    # Act
    with measured(sample_rate=0) as used:
        flag_call("storage_write")
    # Assert
    assert used.exceeded(None, 0) == ["storage_write"]


def test_memory_is_sampled_when_asked():
    # Arrange
    # Act
    with measured(sample_rate=1.0) as used:
        blob = bytearray(4_000_000)
    # Assert
    assert used.peak_memory_bytes >= len(blob)


# ------------------------------------------------------------- real HTTP


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def test_the_tier_over_real_http():
    # Arrange
    from django.core.handlers.wsgi import WSGIHandler

    server = make_server("127.0.0.1", 0, WSGIHandler(), handler_class=_Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/v1/calc/sums/run"
    request = urllib.request.Request(
        url,
        data=json.dumps({"values": [2, 3]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Act
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read())
            klass = response.headers["SciTeX-Priority-Class"]
    finally:
        server.shutdown()
    # Assert
    assert (body["data"]["total"], klass) == (5, "public")


def test_a_dotted_idempotency_store_keeps_its_state_across_requests():
    # Arrange
    tier = {**leaf.TIER, "calc.renders.create": {"public": True, "limits": "light"}}
    with override_settings(SCITEX_API_PUBLIC_TIER=tier):
        _post("/api/v1/calc/renders", {"values": [1]}, key="replay-me")
        # Act
        again = _post("/api/v1/calc/renders", {"values": [1]}, key="replay-me")
    # Assert
    assert again["Idempotent-Replayed"] == "true"


def test_a_literal_action_path_wins_over_an_item_path():
    # Arrange
    from scitex_sdk.app.api_ops import build_plugin
    from scitex_sdk.app.api_plugin import ApiPluginRef
    from scitex_sdk.app.api_serve import api_urlpatterns

    ops = (
        ApiOperation("lit", "tests", "get", "tests._api_ops_tier:create_note"),
        ApiOperation(
            "lit", "tests", "recommend", "tests._api_ops_tier:create_note",
            item=False, read_only=True,
        ),
    )
    leaf.LITERAL_PLUGIN = build_plugin("lit", "Lit", "1", ops)
    ref = ApiPluginRef(name="lit", target="tests._api_ops_tier:LITERAL_PLUGIN")
    # Act
    paths = [str(p.pattern) for p in api_urlpatterns([ref], catch_all=False)]
    # Assert
    assert paths == ["api/v1/lit/tests/recommend", "api/v1/lit/tests/<str:test_id>"]
