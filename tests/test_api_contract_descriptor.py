"""Contract major in the installed descriptor (API-D003) and derived operationIds (API-O001)."""

import dataclasses

from scitex_sdk.app.api_mount import dump_inert_descriptor, parse_inert_descriptor
from scitex_sdk.app.api_ops import operations
from scitex_sdk.app.api_plugin import (
    ApiPluginContractError,
    ApiRoute,
    AuthScope,
    Idempotency,
    RateLimit,
)
from scitex_sdk.app.api_rules import check_contract
from scitex_sdk.testing.api_contract import check_plugin
from tests._api_ops_leaf import PLUGIN


def _raised(call):
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - the tests inspect it
        return exc
    return None


def test_build_plugin_stores_the_declared_contract_major():
    # Arrange
    # Act
    contract = PLUGIN.contract
    # Assert
    assert contract == "1"


def test_the_inert_descriptor_carries_the_contract_major():
    # Arrange
    text = dump_inert_descriptor(PLUGIN)
    # Act
    reread = parse_inert_descriptor(text)
    # Assert
    assert ('"contract": "1"' in text, reread.contract) == (True, "1")


def test_a_descriptor_written_before_the_field_reads_as_contract_one():
    # Arrange
    import json

    data = json.loads(dump_inert_descriptor(PLUGIN))
    del data["contract"]
    for route in data["routes"]:
        del route["operation_id"]
    # Act
    reread = parse_inert_descriptor(json.dumps(data))
    # Assert
    assert (reread.contract, len(operations(reread))) == ("1", len(PLUGIN.routes))


def test_an_unsupported_major_still_parses_so_the_host_can_refuse_it():
    # Arrange
    text = dump_inert_descriptor(dataclasses.replace(PLUGIN, contract="2"))
    # Act
    reread = parse_inert_descriptor(text)
    # Assert
    assert reread.contract == "2"


def test_check_contract_refuses_an_unsupported_major_with_d003():
    # Arrange
    plugin = dataclasses.replace(PLUGIN, contract="2")
    # Act
    exc = _raised(lambda: check_contract(plugin))
    # Assert
    assert (exc.rule, "contract 2 not supported" in str(exc)) == ("API-D003", True)


def test_a_malformed_contract_is_refused_at_construction():
    # Arrange
    # Act
    exc = _raised(lambda: dataclasses.replace(PLUGIN, contract="v1"))
    # Assert
    assert isinstance(exc, ApiPluginContractError)


def test_the_host_refuses_to_mount_an_unsupported_major():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPluginRef
    from scitex_sdk.app.api_serve import REFUSED, admitted_plugins

    ref = ApiPluginRef(
        name="notes-next",
        target="tests._api_ops_contract2:PLUGIN",
        distribution="scitex-notes-next",
    )
    # Act
    admitted = admitted_plugins([ref])
    # Assert
    assert (admitted, REFUSED.get("notes-next", "").startswith("[API-D003]")) == (
        [],
        True,
    )


def test_the_contract_test_reports_an_unsupported_major():
    # Arrange
    plugin = dataclasses.replace(PLUGIN, contract="2")
    # Act
    rules = {v.rule for v in check_plugin(plugin, verb_exceptions={})}
    # Assert
    assert rules == {"API-D003"}


def test_openapi_operation_ids_are_package_resource_verb():
    # Arrange
    fragment = PLUGIN.openapi_fragment()
    # Act
    ids = sorted(
        operation["operationId"]
        for item in fragment["paths"].values()
        for operation in item.values()
    )
    # Assert
    assert ids == sorted(op.operation_id for op in operations(PLUGIN))


def test_a_hand_written_route_keeps_the_injective_id():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPlugin

    plugin = ApiPlugin(
        id="legacy",
        title="Legacy",
        api_version="1",
        routes=(
            ApiRoute(
                path="ping",
                methods=("GET",),
                rate=RateLimit("standard", "light"),
                auth=AuthScope(public=True, project_scope="none"),
                handler="pkg.api:ping",
            ),
        ),
    )
    # Act
    ids = [
        op["operationId"] for op in plugin.openapi_fragment()["paths"]["/ping"].values()
    ]
    # Assert
    assert ids == ["legacy.get.ping"]


def test_an_operation_id_naming_another_package_is_refused():
    # Arrange
    route = dataclasses.replace(PLUGIN.routes[0], operation_id="other.notes.list")
    # Act
    exc = _raised(lambda: dataclasses.replace(PLUGIN, routes=(route,)))
    # Assert
    assert "names another package" in str(exc)


def test_an_operation_id_on_two_methods_is_refused():
    # Arrange
    # Act
    exc = _raised(
        lambda: dataclasses.replace(
            PLUGIN.routes[0],
            methods=("GET", "POST"),
            idempotency=Idempotency(required=True),
            operation_id="notes.notes.list",
        )
    )
    # Assert
    assert "exactly one operation" in str(exc)


def test_a_stored_operation_id_that_disagrees_with_the_route_is_refused():
    # Arrange
    route = dataclasses.replace(PLUGIN.routes[0], operation_id="notes.notes.get")
    plugin = dataclasses.replace(PLUGIN, routes=(route, *PLUGIN.routes[1:]))
    # Act
    exc = _raised(lambda: operations(plugin))
    # Assert
    assert "derives 'notes.notes.list'" in str(exc)
