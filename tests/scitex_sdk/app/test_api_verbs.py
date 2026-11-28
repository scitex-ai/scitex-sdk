"""API-V003: action verbs from the canonical catalogue, or a justified exception."""

from scitex_sdk.app.api_ops import ApiOperation, build_plugin, operations
from scitex_sdk.app.api_verbs import (
    find_dictionary,
    read_verb_exceptions,
    verb_violations,
)
from scitex_sdk.testing.api_contract import check_plugin


def _op(verb):
    return ApiOperation("leaf", "items", verb, "leafpkg.api:handler", item=True)


def _rules(*verbs, exceptions=None):
    return [
        (oid, rule)
        for rule, oid, _m in verb_violations([_op(v) for v in verbs], exceptions or {})
    ]


def test_canonical_action_verbs_pass():
    # Arrange
    # Act
    found = _rules("validate", "copy", "move", "cancel", "export")
    # Assert
    assert found == []


def test_crud_verbs_are_not_judged_as_actions():
    # Arrange
    ops = [ApiOperation("leaf", "items", "get", "leafpkg.api:handler")]
    # Act
    found = verb_violations(ops, {})
    # Assert
    assert found == []


def test_a_synonym_is_refused_with_the_canonical_verb():
    # Arrange
    # Act
    found = verb_violations([_op("verify")], {})
    # Assert
    assert (found[0][0], "use validate" in found[0][2]) == ("API-V003", True)


def test_search_is_never_an_action():
    # Arrange
    # Act
    found = verb_violations([_op("search")], {})
    # Assert
    assert "list with a q parameter" in found[0][2]


def test_an_unknown_verb_is_refused():
    # Arrange
    # Act
    found = _rules("rotate")
    # Assert
    assert found == [("leaf.items.rotate", "API-V003")]


def test_a_compound_action_is_judged_by_its_head_verb():
    # Arrange
    # Act
    found = _rules("read-metadata")
    # Assert
    assert found == []


def test_a_justified_exception_admits_the_verb():
    # Arrange
    # Act
    found = _rules("rotate", exceptions={"rotate": True})
    # Assert
    assert found == []


def test_an_exception_without_a_why_comment_is_reported():
    # Arrange
    # Act
    found = verb_violations([_op("rotate")], {"rotate": False})
    # Assert
    assert "lacks an inline '# why'" in found[0][2]


def test_the_dictionary_reader_reads_only_verb_exceptions(tmp_path):
    # Arrange
    path = tmp_path / "cli-audit-dict.yaml"
    path.write_text(
        "nouns:\n"
        "  - rotate  # why: not a verb here\n"
        "verb_exceptions:\n"
        "  # comment lines are skipped\n"
        "  - rotate  # why: credential rotation is the industry term\n"
        "  - Recommend\n"
        "- verify  # why: provenance, not schema validation\n"
        "transitive_verbs:\n"
        "  - unset\n",
        encoding="utf-8",
    )
    # Act
    found = read_verb_exceptions(path)
    # Assert
    assert found == {"rotate": True, "recommend": False, "verify": True}


def test_a_missing_dictionary_has_no_exceptions(tmp_path):
    # Arrange
    # Act
    found = read_verb_exceptions(tmp_path / "absent.yaml")
    # Assert
    assert found == {}


def test_find_dictionary_is_rooted_at_the_project(tmp_path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    # Act
    found = find_dictionary(nested)
    # Assert
    assert found == tmp_path / ".scitex" / "dev" / "cli-audit-dict.yaml"


def test_the_contract_test_reports_v003():
    # Arrange
    plugin = build_plugin("leaf", "Leaf", "1", (_op("rotate"),))
    # Act
    rules = {v.rule for v in check_plugin(plugin, verb_exceptions={})}
    # Assert
    assert (rules, len(operations(plugin))) == ({"API-V003"}, 1)
