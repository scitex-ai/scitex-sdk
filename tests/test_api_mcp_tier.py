"""The public light compute tier over hosted MCP: the same rules as REST (§12).

A real MCP client over a socket calls an anonymous-capable endpoint serving
the tier test leaf, with ``SCITEX_API_PUBLIC_TIER`` enabling some of its
operations.
"""

import pytest
from django.test import override_settings

from tests import _api_mcp_host as host
from tests import _api_ops_tier as leaf
from tests.test_api_mcp_http import _call, _tool_names, mcp_host  # noqa: F401

TIER = {"SCITEX_API_PUBLIC_TIER": leaf.TIER}


@pytest.fixture(autouse=True)
def _tier():
    host.METERED.clear()
    with override_settings(**TIER):
        yield


def test_anonymous_agents_list_only_the_anonymous_tier_tools(mcp_host):  # noqa: F811
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-tier"
    # Act
    names = _tool_names(url, None)
    # Assert
    assert names == ["calc_sums_run"]


def test_an_anonymous_tool_call_runs_in_the_public_class(mcp_host):  # noqa: F811
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-tier"
    # Act
    result = _call(url, None, "calc_sums_run", {"values": [2, 3]})
    # Assert
    assert (result["structuredContent"]["data"], result["_meta"]["priority_class"]) == (
        {"total": 5, "class": "public"},
        "public",
    )


def test_an_anonymous_tool_call_is_metered_as_sponsored(mcp_host):  # noqa: F811
    # Arrange
    url = f"{mcp_host}/api/v1/mcp-tier"
    # Act
    _call(url, None, "calc_sums_run", {"values": [1]})
    # Assert
    event = host.METERED[-1]
    assert (event["payer"], event["usage_kind"], event["transport"]) == (
        "promotion",
        "public_compute",
        "mcp",
    )


def test_an_anonymous_call_of_a_key_only_tool_says_a_key_is_required(
    mcp_host,  # noqa: F811
):
    # Arrange
    from tests.test_api_mcp_http import _post, _rpc

    url = f"{mcp_host}/api/v1/mcp-tier"
    message = _rpc(
        "tools/call", {"name": "calc_renders_create", "arguments": {"values": [1]}}
    )
    # Act
    _status, _headers, body = _post(url, message, token=None)
    # Assert
    assert b"api.key_required" in body
