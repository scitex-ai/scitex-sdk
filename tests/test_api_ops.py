"""The operation layer: one declaration -> URL, scope, MCP name, route, tool."""

import pytest

from scitex_sdk.app.api_ops import (
    ApiOperation,
    build_plugin,
    operation_of,
    operations,
    scope_granted,
)
from scitex_sdk.app.api_plugin import ApiPluginContractError
from tests._api_ops_leaf import OPERATIONS, PLUGIN


def _raised(call):
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - the tests inspect it
        return exc
    return None


def test_list_url_follows_the_grammar():
    # Arrange
    op = OPERATIONS[0]
    # Act
    url = op.url
    # Assert
    assert url == "/api/v1/notes/notes"


def test_item_action_url_carries_the_id_and_verb():
    # Arrange
    op = OPERATIONS[3]
    # Act
    url = op.url
    # Assert
    assert url == "/api/v1/notes/notes/{note_id}/archive"


def test_read_verbs_need_the_read_scope():
    # Arrange
    op = OPERATIONS[1]
    # Act
    scope = op.scope
    # Assert
    assert scope == "notes:notes:read"


def test_actions_need_the_write_scope():
    # Arrange
    op = OPERATIONS[3]
    # Act
    scope = op.scope
    # Assert
    assert scope == "notes:notes:write"


def test_mcp_names_are_derived():
    # Arrange
    ops = OPERATIONS
    # Act
    names = [op.mcp_name for op in ops]
    # Assert
    assert names == [
        "notes_notes_list",
        "notes_notes_get",
        "notes_notes_create",
        "notes_notes_archive",
    ]


def test_create_answers_201():
    # Arrange
    op = OPERATIONS[2]
    # Act
    status = op.success_status
    # Assert
    assert status == 201


def test_a_job_response_answers_202():
    # Arrange
    op = OPERATIONS[3]
    # Act
    status = op.success_status
    # Assert
    assert status == 202


def test_the_plugin_round_trips_to_its_operations():
    # Arrange
    plugin = PLUGIN
    # Act
    derived = [(op.mcp_name, op.summary, op.paginated) for op in operations(plugin)]
    # Assert
    assert derived[0] == ("notes_notes_list", "Search notes", True)


def test_the_openapi_fragment_names_the_derived_scope():
    # Arrange
    plugin = PLUGIN
    # Act
    fragment = plugin.openapi_fragment()
    # Assert
    assert "notes:notes:write" in str(fragment)


def test_a_singular_resource_is_refused():
    # Arrange
    build = lambda: ApiOperation("notes", "note", "list", "m:f")
    # Act
    raised = _raised(build)
    # Assert
    assert isinstance(raised, ApiPluginContractError)


def test_an_action_must_say_item_or_collection():
    # Arrange
    build = lambda: ApiOperation("notes", "notes", "archive", "m:f")
    # Act
    raised = _raised(build)
    # Assert
    assert isinstance(raised, ApiPluginContractError)


def test_operations_of_another_package_are_refused():
    # Arrange
    foreign = ApiOperation("other", "notes", "list", "m:f", paginated=True)
    # Act
    raised = _raised(lambda: build_plugin("notes", "N", "1", [foreign]))
    # Assert
    assert isinstance(raised, ApiPluginContractError)


def test_a_hand_written_route_off_the_grammar_is_not_an_operation():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiRoute, AuthScope, RateLimit

    route = ApiRoute(
        "notes/{note_id}",
        ("GET",),
        RateLimit("standard", "light"),
        path_params=("note_id",),
        auth=AuthScope(scopes=("notes:other:read",)),
        handler="m:f",
    )
    # Act
    raised = _raised(lambda: operation_of(PLUGIN, route))
    # Assert
    assert isinstance(raised, ApiPluginContractError)


@pytest.mark.parametrize(
    ("granted", "ok"),
    [
        (("*",), True),
        (("*:read",), True),
        (("notes:*:read",), True),
        (("notes:notes:write",), True),
        (("notes:*:write",), True),
        (("other:*:read",), False),
        (("notes:tags:read",), False),
        ((), False),
    ],
)
def test_read_scope_grants(granted, ok):
    # Arrange
    required = "notes:notes:read"
    # Act
    result = scope_granted(required, granted)
    # Assert
    assert result is ok


def test_read_never_grants_write():
    # Arrange
    granted = ("notes:*:read",)
    # Act
    result = scope_granted("notes:notes:write", granted)
    # Assert
    assert result is False


LEAF_SOURCE = """
from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiField

OPERATIONS = (
    ApiOperation("leaf", "items", "list", "leafpkg._api:list_items",
                 params=(ApiField("q", "string", False),), paginated=True),
)
PLUGIN = build_plugin("leaf", "Leaf API", "1", OPERATIONS)


def list_items(call):
    raise RuntimeError("never executed by the source reader")
"""


def test_the_source_reader_proves_an_operation_declaration(tmp_path):
    # Arrange
    from scitex_sdk.app._api_source import SourceReader

    (tmp_path / "src" / "leafpkg").mkdir(parents=True)
    (tmp_path / "src" / "leafpkg" / "__init__.py").write_text("")
    (tmp_path / "src" / "leafpkg" / "_api.py").write_text(LEAF_SOURCE)
    # Act
    plugin = SourceReader(tmp_path).binding("leafpkg._api", "PLUGIN")
    # Assert
    assert [op.url for op in operations(plugin)] == ["/api/v1/leaf/items"]
