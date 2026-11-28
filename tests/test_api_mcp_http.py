"""Hosted MCP over real HTTP, exercised by the official MCP Python client.

A Django host (tests/_api_mcp_host.py) serves the notes and catalog test
leaves at /api/v1/mcp on a real socket. The MCP SDK's Streamable HTTP client
connects with a bearer key, lists tools, calls them, and validates
structured results against the advertised output schemas. Transport-level
behaviour the client hides (401 challenge, 405, Origin, protocol errors) is
checked with plain HTTP requests.
"""

import json
import threading
import urllib.error
import urllib.request
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import anyio
import pytest
from django.core.handlers.wsgi import WSGIHandler
from django.test import override_settings

from tests import _api_mcp_host as host

try:  # mcp >= 2 ships its HTTP stack on httpx2
    import httpx2 as httpx
except ImportError:  # pragma: no cover - mcp 1.x
    import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

HOOKS = dict(
    ROOT_URLCONF="tests._api_mcp_host",
    SCITEX_API_CALLER="tests._api_mcp_host.caller",
    SCITEX_API_RATE_LIMITER="tests._api_mcp_host.Limiter",
    SCITEX_API_METER="tests._api_mcp_host.Meter",
    SCITEX_API_IDEMPOTENCY_STORE=host.STORE,
)


class _Server(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def mcp_host():
    with override_settings(**HOOKS):
        server = make_server(
            "127.0.0.1", 0, WSGIHandler(), _Server, handler_class=_QuietHandler
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()


@pytest.fixture(autouse=True)
def _fresh_host(tmp_path):
    host.METERED.clear()
    host.LIMITED["on"] = False
    host.PROJECT_ROOTS.clear()
    host.PROJECT_ROOTS["alice/notes"] = str(tmp_path)


def _session(url, token, steps):
    """Run ``steps(session)`` in a real MCP client session; return its value."""

    async def main():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with httpx.AsyncClient(headers=headers, timeout=10) as http:
            async with streamable_http_client(url, http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await steps(session)

    return anyio.run(main)


def _tool_names(url, token):
    async def steps(session):
        return sorted(t.name for t in (await session.list_tools()).tools)

    return _session(url, token, steps)


def _call(url, token, name, arguments):
    async def steps(session):
        await session.list_tools()  # the client validates outputs against these
        result = await session.call_tool(name, arguments)
        return result.model_dump(by_alias=True, mode="json")

    return _session(url, token, steps)


def _post(url, message, token="read-token", **headers):
    data = json.dumps(message).encode()
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/event-stream")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for key, value in headers.items():
        request.add_header(key.replace("_", "-"), value)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            return response.status, dict(response.headers), body
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def _rpc(method, params=None, rpc_id=1):
    return {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}


# ---------------------------------------------------------------- tools/list


def test_a_read_key_lists_its_read_tools_and_the_public_ones(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    names = _tool_names(url, "read-token")
    # Assert
    assert names == ["catalog_entries_list", "notes_notes_get", "notes_notes_list"]


def test_a_write_key_also_lists_write_tools_below_its_tier(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    names = _tool_names(url, "write-token")
    # Assert
    assert "notes_notes_create" in names and "notes_notes_archive" not in names


def test_a_paid_key_lists_the_paid_tier_tool(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    names = _tool_names(url, "paid-token")
    # Assert
    assert "notes_notes_archive" in names


def test_a_key_scoped_to_another_package_sees_none_of_its_tools(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    names = _tool_names(url, "catalog-only")
    # Assert
    assert names == ["catalog_entries_list"]


def test_listed_tools_carry_derived_schemas_and_rest_docs(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"

    async def steps(session):
        tools = {t.name: t for t in (await session.list_tools()).tools}
        return tools["notes_notes_list"].model_dump(by_alias=True, mode="json")

    # Act
    tool = _session(url, "read-token", steps)
    # Assert
    assert (
        tool["inputSchema"]["properties"]["q"]["type"],
        tool["outputSchema"]["required"],
        "GET /api/v1/notes/notes" in tool["description"],
    ) == ("string", ["data", "has_more", "next_cursor"], True)


def test_without_a_key_an_open_endpoint_lists_public_tools_only(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-open"
    # Act
    names = _tool_names(url, None)
    # Assert
    assert names == ["catalog_entries_list"]


# ---------------------------------------------------------------- tools/call


def test_a_call_returns_the_rest_body_as_structured_content(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_list", {"q": "Note"})
    # Assert
    assert (
        result["isError"],
        [n["id"] for n in result["structuredContent"]["data"]],
        result["structuredContent"]["has_more"],
    ) == (False, ["n0", "n1"], True)


def test_a_call_names_its_request_and_operation_in_meta(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_list", {})
    # Assert
    assert (len(result["_meta"]["request_id"]), result["_meta"]["operation_id"]) == (
        32,
        "notes.notes.list",
    )


def test_a_call_also_returns_the_body_as_text(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_get", {"note_id": "n3"})
    # Assert
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_a_leaf_refusal_is_an_error_result_with_the_problem(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_get", {"note_id": "nope"})
    # Assert
    problem = result["structuredContent"]
    assert (result["isError"], problem["status"], problem["code"]) == (
        True,
        404,
        "notes.not_found",
    )


def test_the_problem_and_meta_share_one_request_id(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_get", {"note_id": "nope"})
    # Assert
    assert result["structuredContent"]["request_id"] == result["_meta"]["request_id"]


def test_a_bad_argument_is_a_tool_error_the_model_can_correct(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "read-token", "notes_notes_list", {"limit": 99})
    # Assert
    assert (result["isError"], result["structuredContent"]["code"]) == (
        True,
        "api.invalid_parameter",
    )


def test_calling_an_unlisted_tool_names_the_missing_scope(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    message = _rpc("tools/call", {"name": "notes_notes_create", "arguments": {}})
    # Act
    _, _, body = _post(url, message, token="read-token")
    # Assert
    result = json.loads(body)["result"]
    assert (result["isError"], result["structuredContent"]["required_scope"]) == (
        True,
        "notes:notes:write",
    )


def test_calling_a_tool_above_the_key_tier_names_the_tier(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    message = _rpc(
        "tools/call", {"name": "notes_notes_archive", "arguments": {"note_id": "n1"}}
    )
    # Act
    _, _, body = _post(url, message, token="write-token")
    # Assert
    assert json.loads(body)["result"]["structuredContent"]["required_tier"] == "paid"


def test_an_async_operation_answers_its_job(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    result = _call(url, "paid-token", "notes_notes_archive", {"note_id": "n1"})
    # Assert
    assert result["structuredContent"]["job"]["id"] == "job_1"


def test_a_project_token_defaults_the_project(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-explicit"
    # Act
    result = _call(url, "project-token", "notes_notes_create", {"title": "T"})
    # Assert
    assert result["structuredContent"]["data"]["project"] == "alice/notes"


def test_a_project_token_cannot_reach_another_project(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-explicit"
    arguments = {"title": "T", "project": "bob/other"}
    # Act
    result = _call(url, "project-token", "notes_notes_create", arguments)
    # Assert
    assert (result["isError"], result["structuredContent"]["status"]) == (True, 403)


def test_every_call_is_metered_as_mcp(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    _call(url, "read-token", "notes_notes_list", {})
    # Assert
    assert [(e["operation_id"], e["transport"]) for e in host.METERED] == [
        ("notes.notes.list", "mcp")
    ]


def test_the_host_rate_limiter_refuses_a_call(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    host.LIMITED["on"] = True
    # Act
    result = _call(url, "read-token", "notes_notes_list", {})
    # Assert
    assert result["structuredContent"]["status"] == 429


def test_a_client_idempotency_key_replays_a_write(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-explicit"
    params = {
        "name": "notes_notes_create",
        "arguments": {"title": "Once", "project": "alice/notes"},
        "_meta": {"idempotency_key": "create-once"},
    }
    _post(url, _rpc("tools/call", params), token="write-token")
    # Act
    _, _, body = _post(url, _rpc("tools/call", params, 2), token="write-token")
    # Assert
    assert json.loads(body)["result"]["_meta"]["idempotent_replayed"] is True


# ---------------------------------------------------------------- transport


def test_no_key_is_a_401_challenge(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-explicit"
    # Act
    status, headers, _ = _post(url, _rpc("tools/list"), token=None)
    # Assert
    assert (status, headers["WWW-Authenticate"]) == (
        401,
        'Bearer realm="scitex", resource_metadata="https://h.example/prm"',
    )


def test_an_invalid_key_is_a_401_invalid_token(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    status, headers, body = _post(url, _rpc("tools/list"), token="bogus")
    # Assert
    assert (status, 'error="invalid_token"' in headers["WWW-Authenticate"]) == (
        401,
        True,
    )


def test_get_is_405_since_no_stream_is_offered(mcp_host):
    # Arrange
    request = urllib.request.Request(f"{mcp_host}/api/v1/mcp", method="GET")
    # Act
    try:
        urllib.request.urlopen(request, timeout=10)
        status = 200
    except urllib.error.HTTPError as err:
        status = err.code
    # Assert
    assert status == 405


def test_a_foreign_origin_is_403(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    status, _, _ = _post(url, _rpc("ping"), Origin="https://evil.example")
    # Assert
    assert status == 403


def test_an_unknown_tool_is_a_json_rpc_invalid_params_error(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    _, _, body = _post(url, _rpc("tools/call", {"name": "no_such_tool"}))
    # Assert
    assert json.loads(body)["error"]["code"] == -32602  # stx-allow: STX-NL001


def test_an_unsupported_protocol_version_is_400(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    # Act
    status, _, _ = _post(url, _rpc("ping"), MCP_Protocol_Version="1999-01-01")
    # Assert
    assert status == 400


def test_a_notification_is_accepted_without_a_body(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    # Act
    status, _, body = _post(url, message)
    # Assert
    assert (status, body) == (202, b"")


def test_initialize_negotiates_a_supported_version(mcp_host):
    # Arrange
    url = f"{mcp_host}/api/v1/mcp"
    params = {"protocolVersion": "2030-01-01", "capabilities": {}, "clientInfo": {}}
    # Act
    _, _, body = _post(url, _rpc("initialize", params))
    # Assert
    assert json.loads(body)["result"]["protocolVersion"] == "2025-11-25"
