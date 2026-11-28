"""Normalization rules over real path shapes taken from the operation grammar."""

from scitex_sdk.app.api_inventory import RULES, mcp_name_rules, path_rules, route_rules
from scitex_sdk.app.api_ops import ApiOperation


def test_a_derived_operation_url_violates_no_path_rule():
    # Arrange
    op = ApiOperation("clew", "claims", "verify", "x:y", item=True)
    # Act
    found = path_rules(op.url)
    # Assert
    assert found == []


def test_a_legacy_verb_path_is_unversioned_with_a_verb_and_a_slash():
    # Arrange
    path = "/api/project/create/"
    # Act
    found = set(path_rules(path))
    # Assert
    assert {"API-R001", "API-V002", "API-R004"} <= found


def test_an_action_verb_as_the_final_segment_is_allowed():
    # Arrange
    path = "/api/v1/writer/manuscripts/{manuscript_id}/compile"
    # Act
    found = path_rules(path)
    # Assert
    assert "API-V002" not in found


def test_an_action_verb_before_the_resource_is_flagged():
    # Arrange
    path = "/api/v1/writer/compile/manuscripts"
    # Act
    found = path_rules(path)
    # Assert
    assert "API-V002" in found


def test_a_singular_resource_is_flagged():
    # Arrange
    path = "/api/v1/scholar/search"
    # Act
    found = path_rules(path)
    # Assert
    assert "API-R003" in found


def test_snake_case_segments_are_flagged():
    # Arrange
    path = "/api/v1/hub/user_profiles"
    # Act
    found = path_rules(path)
    # Assert
    assert "API-R002" in found


def test_an_unauthenticated_csrf_exempt_write_is_flagged():
    # Arrange
    row = {
        "path": "/api/stats/calculate/",
        "methods": ["POST"],
        "auth": ["none"],
        "csrf_exempt": True,
        "owner_kind": "hub",
    }
    # Act
    found = set(route_rules(row))
    # Assert
    assert {"API-A001", "API-A004"} <= found


def test_a_signed_webhook_is_neither_anonymous_nor_keyless():
    # Arrange
    row = {
        "path": "/api/hooks/",
        "methods": ["POST"],
        "auth": ["signature"],
        "csrf_exempt": True,
        "owner_kind": "hub",
    }
    # Act
    found = set(route_rules(row))
    # Assert
    assert not {"API-A001", "API-A001", "API-A004"} & found


def test_a_contract_route_with_its_twin_conforms():
    # Arrange
    row = {
        "path": "/api/v1/notes/notes",
        "methods": ["GET"],
        "auth": ["contract"],
        "contract": True,
        "mcp_twin": "notes_notes_list",
    }
    # Act
    found = route_rules(row)
    # Assert
    assert found == []


def test_a_repeated_namespace_is_a_double_prefix():
    # Arrange
    name = "clew_clew_add_claim"
    # Act
    found = mcp_name_rules(name, "clew", False)
    # Assert
    assert "API-T003" in found


def test_a_multi_word_namespace_repeated_is_a_double_prefix():
    # Arrange
    name = "live_paper_live_paper_render"
    # Act
    found = mcp_name_rules(name, "live_paper", True)
    # Assert
    assert "API-T003" in found


def test_a_derived_tool_name_conforms():
    # Arrange
    name = "dataset_datasets_list"
    # Act
    found = mcp_name_rules(name, "dataset", True)
    # Assert
    assert found == []


def test_an_underived_tool_breaks_parity_and_grammar():
    # Arrange
    name = "db_search"
    # Act
    found = set(mcp_name_rules(name, "dataset", False))
    # Assert
    assert {"API-T002", "API-T001"} <= found


def test_every_rule_has_a_title_and_a_check():
    # Arrange
    rules = RULES.values()
    # Act
    complete = [bool(title and check) for title, check in rules]
    # Assert
    assert all(complete)
