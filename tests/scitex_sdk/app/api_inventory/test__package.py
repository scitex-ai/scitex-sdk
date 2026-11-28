"""One package's listing: declared operations + its real FastMCP server."""

import pytest

from scitex_sdk.app.api_inventory import PackageSpec, list_package
from scitex_sdk.app.api_inventory._hosted import hosted_entries
from tests._api_ops_host import REF

SPEC = PackageSpec(
    "scitex-notes", import_name="tests", mcp_server="tests._api_inventory_mcp:mcp"
)


@pytest.fixture(scope="module")
def listing():
    return list_package(SPEC, refs=[REF])


def test_every_declared_operation_is_listed(listing):
    # Arrange
    expected = {
        "notes.notes.list",
        "notes.notes.get",
        "notes.notes.create",
        "notes.notes.archive",
    }
    # Act
    ids = {row["operation_id"] for row in listing.operations}
    # Assert
    assert ids == expected


def test_an_action_operation_carries_its_derived_facts(listing):
    # Arrange
    ops = {row["operation_id"]: row for row in listing.operations}
    # Act
    archive = ops["notes.notes.archive"]
    # Assert
    assert (archive["path"], archive["methods"], archive["mcp_twin"]) == (
        "/api/v1/notes/notes/{note_id}/archive",
        ["POST"],
        "notes_notes_archive",
    )


def test_declared_operations_conform_and_their_twins_are_served(listing):
    # Arrange
    ops = listing.operations
    # Act
    clean = [row["violations"] == [] and row["mcp_twin_served"] for row in ops]
    # Assert
    assert all(clean)


def test_a_derived_tool_conforms(listing):
    # Arrange
    tools = {row["name"]: row for row in listing.mcp_tools}
    # Act
    row = tools["notes_notes_list"]
    # Assert
    assert (row["derived_from_operation"], row["violations"]) == (True, [])


def test_a_hand_written_tool_is_flagged(listing):
    # Arrange
    tools = {row["name"]: row for row in listing.mcp_tools}
    # Act
    legacy = tools["notes_notes_legacy_dump"]
    # Assert
    assert (
        legacy["input"],
        {"API-N08", "API-N09", "API-N10"} <= set(legacy["violations"]),
    ) == ("limit", True)


def test_another_distribution_lists_none_of_these_operations():
    # Arrange
    spec = PackageSpec("scitex-other", import_name="tests")
    # Act
    other = list_package(spec, refs=[REF])
    # Assert
    assert other.operations == []


def test_a_hosted_aggregate_attributes_tools_to_their_namespace():
    # Arrange
    from tests._api_inventory_mcp import hosted

    # Act
    rows = {
        row["name"]: row
        for row in hosted_entries(hosted, derived_names={"notes_notes_list"})
    }
    # Assert
    row = rows["notes_notes_notes_list"]
    assert (row["namespace"], row["raw_name"], "API-N09" in row["violations"]) == (
        "notes",
        "notes_notes_list",
        True,
    )
