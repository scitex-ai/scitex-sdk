"""The shipped contract test, run against a real declared leaf and real routes."""

from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiField
from scitex_sdk.testing.api_contract import (
    assert_contract,
    check_plugin,
    compare,
    run_contract_suite,
)
from tests._api_ops_leaf import OPERATIONS, PLUGIN

TARGET = "tests._api_ops_leaf:PLUGIN"


def _contract_error(plugin, **kwargs):
    try:
        assert_contract(plugin, target=TARGET, **kwargs)
    except AssertionError as exc:
        return str(exc)
    return None


def test_a_conforming_leaf_passes_the_whole_contract():
    # Arrange
    previous = PLUGIN
    # Act
    error = _contract_error(PLUGIN, previous=previous)
    # Assert
    assert error is None


def test_the_static_check_finds_nothing_on_a_conforming_leaf():
    # Arrange
    plugin = PLUGIN
    # Act
    found = check_plugin(plugin)
    # Assert
    assert found == []


def test_the_served_suite_probes_every_operation_over_http():
    # Arrange
    plugin = PLUGIN
    # Act
    found = run_contract_suite(plugin, target=TARGET)
    # Assert
    assert found == []


def test_removing_an_operation_breaks_compatibility():
    # Arrange
    smaller = build_plugin("notes", "Notes API", "1", OPERATIONS[:-1])
    # Act
    found = compare(PLUGIN, smaller)
    # Assert
    assert [(v.rule, v.operation_id) for v in found] == [
        ("API-C001", "notes.notes.archive")
    ]


def test_a_new_required_parameter_breaks_compatibility():
    # Arrange
    first = OPERATIONS[0]
    stricter = ApiOperation(
        "notes",
        "notes",
        "list",
        first.handler,
        params=(ApiField("q", "string", True, "Text query"),),
        paginated=True,
        default_limit=2,
        max_limit=3,
    )
    current = build_plugin("notes", "Notes API", "1", (stricter, *OPERATIONS[1:]))
    # Act
    found = compare(PLUGIN, current)
    # Assert
    assert [str(v) for v in found] == [
        "[API-C001] notes.notes.list: parameters became required ['q']"
    ]


def test_an_added_operation_is_compatible():
    # Arrange
    extra = ApiOperation(
        "notes", "tags", "list", "tests._api_ops_leaf:list_notes", paginated=True
    )
    current = build_plugin("notes", "Notes API", "1", (*OPERATIONS, extra))
    # Act
    found = compare(PLUGIN, current)
    # Assert
    assert found == []


def test_assert_contract_reports_every_violation_with_its_rule():
    # Arrange
    smaller = build_plugin("notes", "Notes API", "1", OPERATIONS[:1])
    # Act
    error = _contract_error(smaller, previous=PLUGIN)
    # Assert
    assert error.count("[API-C001]") == 3
