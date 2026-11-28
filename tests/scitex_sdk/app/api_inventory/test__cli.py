"""The shared ``api list`` command and the SDK's own ``scitex-sdk api``."""

import csv
import io
import json

import pytest
from click.testing import CliRunner

from scitex_sdk.app.api_inventory import (
    PackageSpec,
    aggregate,
    api_click_group,
    to_csv,
    to_markdown,
)
from scitex_sdk.cli import main

NOTES = PackageSpec(
    "scitex-notes", import_name="tests", mcp_server="tests._api_inventory_mcp:mcp"
)


@pytest.fixture(scope="module")
def notes_doc():
    return aggregate([NOTES])


def test_scitex_sdk_api_list_shows_its_own_conformant_operation():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(main, ["api", "list", "--json"])
    # Assert
    skills = next(
        e
        for e in json.loads(result.output)["entries"]
        if e.get("path") == "/api/v1/sdk/skills"
    )
    assert (skills["operation_id"], skills["violations"]) == ("sdk.skills.list", [])


def test_strict_list_fails_when_a_rule_is_violated():
    # Arrange
    group = api_click_group(
        "scitex-notes", import_name="tests", mcp_server="tests._api_inventory_mcp:mcp"
    )
    # Act
    result = CliRunner().invoke(group, ["list", "--strict", "--format", "md"])
    # Assert
    assert (result.exit_code, "violate API rules" in result.output) == (1, True)


def test_a_leaf_gets_the_same_command_bound_to_its_package(tmp_path):
    # Arrange
    group = api_click_group(
        "scitex-notes", import_name="tests", mcp_server="tests._api_inventory_mcp:mcp"
    )
    out = tmp_path / "notes.json"
    # Act
    CliRunner().invoke(group, ["list", "--format", "json", "-o", str(out)])
    # Assert
    names = {e.get("name") for e in json.loads(out.read_text())["entries"]}
    assert "notes_notes_legacy_dump" in names


def test_csv_has_one_row_per_entry(notes_doc):
    # Arrange
    text = to_csv(notes_doc)
    # Act
    rows = list(csv.DictReader(io.StringIO(text)))
    # Assert
    assert len(rows) == len(notes_doc["entries"])


def test_markdown_carries_totals_and_entries(notes_doc):
    # Arrange
    doc = notes_doc
    # Act
    md = to_markdown(doc)
    # Assert
    assert ("### By violated rule" in md, "notes_notes_legacy_dump" in md) == (
        True,
        True,
    )
