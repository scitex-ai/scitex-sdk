"""The SDK's own API is declared as contract operations and passes the contract."""

from pathlib import Path

from scitex_sdk._web._api import plugin
from scitex_sdk.app._api_contract import scan_api_contract, scan_web_contract
from scitex_sdk.app.api_exec import ApiCaller, execute
from scitex_sdk.app.api_ops import operations
from scitex_sdk.testing.api_contract import assert_contract

ROOT = Path(__file__).resolve().parents[3]
TARGET = "scitex_sdk._web._api:plugin"


def _contract_error():
    try:
        assert_contract(plugin, target=TARGET)
    except AssertionError as exc:
        return str(exc)
    return None


def test_the_sdk_api_is_one_public_paginated_list():
    # Arrange
    (op,) = operations(plugin)
    # Act
    shape = (op.url, op.method, op.public, op.paginated, op.mcp_name)
    # Assert
    assert shape == ("/api/v1/sdk/skills", "GET", True, True, "sdk_skills_list")


def test_the_sdk_api_passes_its_own_contract_test():
    # Arrange
    expected = None
    # Act
    error = _contract_error()
    # Assert
    assert error == expected


def test_listing_skills_returns_ids_without_paths():
    # Arrange
    (op,) = operations(plugin)
    anonymous = ApiCaller(user=None, scopes=(), via="anonymous")
    # Act
    result = execute(op, anonymous, {"limit": "200"})
    # Assert
    assert [r for r in result.body["data"] if r["skill_id"].startswith("/")] == []


def test_sdk_source_passes_its_own_quality_rule():
    # Arrange
    root = ROOT
    # Act
    findings = scan_web_contract(root)
    # Assert
    assert findings == []


def test_sdk_source_passes_the_api_contract_audit():
    # Arrange
    root = ROOT
    # Act
    findings = scan_api_contract(root)
    # Assert
    assert findings == []
