"""Generic serving of declared operations, through the host's hooks."""

import json

import pytest
from django.test import Client, override_settings

from scitex_sdk.app.api_exec import ApiCaller, execute
from scitex_sdk.app.api_mcp import call_tool, tool_specs
from tests import _api_ops_host as host
from tests._api_ops_leaf import PLUGIN

HOOKS = dict(
    ROOT_URLCONF="tests._api_ops_host",
    SCITEX_API_CALLER="tests._api_ops_host.caller",
    SCITEX_API_RATE_LIMITER="tests._api_ops_host.Limiter",
    SCITEX_API_METER="tests._api_ops_host.Meter",
    SCITEX_API_IDEMPOTENCY_STORE=host.STORE,
)


@pytest.fixture
def api():
    host.METERED.clear()
    host.LIMITED["on"] = False
    with override_settings(**HOOKS):
        yield Client()


def _get(client, url, token="read-token", **params):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return client.get(url, params, **headers)


def _post(client, url, data, token="write-token", key="k1"):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    if key:
        headers["HTTP_IDEMPOTENCY_KEY"] = key
    return client.post(
        url, json.dumps(data), content_type="application/json", **headers
    )


def test_a_read_token_can_list(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _get(api, url, q="Note")
    # Assert
    assert [n["id"] for n in response.json()["data"]] == ["n0", "n1"]


def test_a_list_page_carries_a_cursor(api):
    # Arrange
    first = _get(api, "/api/v1/notes/notes").json()
    # Act
    second = _get(api, "/api/v1/notes/notes", cursor=first["next_cursor"]).json()
    # Assert
    assert [n["id"] for n in second["data"]] == ["n2", "n3"]


def test_no_credential_is_a_401_problem(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _get(api, url, token=None)
    # Assert
    assert (response.status_code, response["Content-Type"]) == (
        401,
        "application/problem+json",
    )


def test_a_401_never_redirects(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _get(api, url, token="bogus")
    # Assert
    assert response.json()["code"] == "api.unauthenticated"


def test_a_read_token_cannot_write(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _post(api, url, {"project": "o/p", "title": "x"}, token="read-token")
    # Assert
    assert response.json()["code"] == "api.insufficient_scope"


def test_a_write_needs_an_idempotency_key(api):
    # Arrange
    url = "/api/v1/notes/notes/n1/archive"
    # Act
    response = _post(api, url, {}, key=None)
    # Assert
    assert response.json()["code"] == "api.idempotency_key_required"


def test_an_async_action_answers_202_with_a_job(api):
    # Arrange
    url = "/api/v1/notes/notes/n1/archive"
    # Act
    response = _post(api, url, {}, key="arch-1")
    # Assert
    assert (response.status_code, response.json()["job"]["id"]) == (202, "job_1")


def test_a_replayed_key_returns_the_first_answer(api):
    # Arrange
    url = "/api/v1/notes/notes/n2/archive"
    _post(api, url, {}, key="arch-2")
    # Act
    replay = _post(api, url, {}, key="arch-2")
    # Assert
    assert replay["Idempotent-Replayed"] == "true"


def test_a_reused_key_with_other_parameters_is_409(api):
    # Arrange
    _post(api, "/api/v1/notes/notes/n3/archive", {}, key="arch-3")
    # Act
    response = _post(api, "/api/v1/notes/notes/n4/archive", {}, key="arch-3")
    # Assert
    assert response.status_code == 409


def test_an_unknown_parameter_is_400(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _get(api, url, color="red")
    # Assert
    assert response.json()["code"] == "api.unknown_parameter"


def test_a_leaf_problem_keeps_its_code(api):
    # Arrange
    url = "/api/v1/notes/notes/nope"
    # Act
    response = _get(api, url)
    # Assert
    assert (response.status_code, response.json()["code"]) == (404, "notes.not_found")


def test_the_wrong_method_is_405(api):
    # Arrange
    url = "/api/v1/notes/notes/n1"
    # Act
    response = api.delete(url, HTTP_AUTHORIZATION="Bearer read-token")
    # Assert
    assert response.status_code == 405


def test_an_unknown_api_path_is_a_problem_not_html(api):
    # Arrange
    url = "/api/v1/nothing/here"
    # Act
    response = _get(api, url)
    # Assert
    assert response["Content-Type"] == "application/problem+json"


def test_the_host_limiter_refuses_with_retry_after(api):
    # Arrange
    host.LIMITED["on"] = True
    # Act
    response = _get(api, "/api/v1/notes/notes")
    # Assert
    assert (response.status_code, response["Retry-After"]) == (429, "7")


def test_the_host_meter_records_every_call(api):
    # Arrange
    _get(api, "/api/v1/notes/notes")
    # Act
    events = [(e["operation_id"], e["status"]) for e in host.METERED]
    # Assert
    assert events == [("notes.notes.list", 200)]


def test_every_response_carries_a_request_id(api):
    # Arrange
    url = "/api/v1/notes/notes"
    # Act
    response = _get(api, url)
    # Assert
    assert len(response["X-Request-Id"]) == 32


def test_without_a_caller_hook_the_api_is_unavailable(api, settings):
    # Arrange
    settings.SCITEX_API_CALLER = None
    # Act
    response = _get(api, "/api/v1/notes/notes")
    # Assert
    assert response.status_code == 503


# --- MCP: the same operations, 1:1 ------------------------------------------


def test_every_operation_is_one_mcp_tool():
    # Arrange
    plugin = PLUGIN
    # Act
    names = [spec.name for spec in tool_specs(plugin)]
    # Assert
    assert names == [
        "notes_notes_list",
        "notes_notes_get",
        "notes_notes_create",
        "notes_notes_archive",
    ]


def test_the_tool_schema_is_the_request_schema():
    # Arrange
    spec = tool_specs(PLUGIN)[0]
    # Act
    properties = sorted(spec.input_schema["properties"])
    # Assert
    assert properties == ["cursor", "limit", "q"]


def test_the_mcp_tool_returns_the_rest_body(api):
    # Arrange
    spec = tool_specs(PLUGIN)[0]
    rest = _get(api, "/api/v1/notes/notes", q="Note 4").json()
    # Act
    body = call_tool(spec, {"q": "Note 4"})
    # Assert
    assert body == rest


def test_the_mcp_tool_obeys_the_same_scopes():
    # Arrange
    spec = tool_specs(PLUGIN)[3]
    caller = ApiCaller(user=None, scopes=("notes:*:read",))
    # Act
    result = execute(spec.operation, caller, {}, item_id="n1")
    # Assert
    assert result.body["code"] == "api.insufficient_scope"


def test_discovery_admits_only_trusted_distributions(settings):
    # Arrange
    from scitex_sdk.app.api_serve import admitted_plugins

    settings.SCITEX_API_TRUSTED_DISTRIBUTIONS = ()
    # Act
    admitted = admitted_plugins()
    # Assert
    assert admitted == []


def test_a_plugin_off_the_operation_grammar_is_refused_not_mounted():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPluginRef
    from scitex_sdk.app.api_serve import REFUSED, admitted_plugins

    ref = ApiPluginRef(
        name="scitex-sdk", target="scitex_sdk._web._api:plugin", distribution="scitex-sdk"
    )
    # Act
    admitted = admitted_plugins([ref])
    # Assert
    assert (admitted, "scitex-sdk" in REFUSED) == ([], True)


def test_the_cache_store_replays_through_the_django_cache():
    # Arrange
    from scitex_sdk.app.api_serve import CacheIdempotencyStore

    store = CacheIdempotencyStore()
    store.put(("a", "op", "k"), "d", 201, {"data": 1})
    # Act
    found = store.get(("a", "op", "k"))
    # Assert
    assert found == ("d", 201, {"data": 1})
