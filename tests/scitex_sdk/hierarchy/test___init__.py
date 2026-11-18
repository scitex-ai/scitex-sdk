"""Stable hierarchy identities, tree integrity and leaf ownership."""

from dataclasses import replace
from itertools import permutations

import pytest
import tomllib

from scitex_sdk.hierarchy import (
    HierarchyNode,
    get_hierarchy_nodes,
    hierarchy_breadcrumbs,
    validate_hierarchy,
)
from tests._checkout import REPO_ROOT


def _nodes():
    return (
        HierarchyNode("scitex", "0", "SciTeX", None),
        HierarchyNode("scitex.applications", "2", "Applications", "scitex"),
        *get_hierarchy_nodes(),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", ""),
        ("id", " x"),
        ("id", 1),
        ("id", "x\ny"),
        ("index", True),
        ("index", "01"),
        ("index", "2.0"),
        ("index", "-1"),
        ("index", "2..5"),
        ("index", "2.05"),
        ("label", ""),
        ("label", "a\tb"),
        ("label", None),
        ("parent_id", ""),
        ("parent_id", False),
        ("distribution", "SciTeX-SDK"),
        ("distribution", "scitex_sdk"),
        ("distribution", "scitex.sdk"),
        ("distribution", "other"),
        ("distribution", None),
    ],
)
def test_malformed_node_fields_are_refused(field, value):
    # Arrange
    node = get_hierarchy_nodes()[0]
    # Act
    # Assert
    with pytest.raises(ValueError, match="hierarchy"):
        replace(node, **{field: value})


def test_every_discovery_permutation_keeps_the_same_indices_and_order():
    # Arrange
    nodes = _nodes()
    expected = ["0", "2", "2.5"]
    # Act
    results = [
        [n.index for n in validate_hierarchy(order)] for order in permutations(nodes)
    ]
    # Assert
    assert results == [expected] * 6


def test_indices_sort_numerically_instead_of_lexically():
    # Arrange
    nodes = (
        HierarchyNode("scitex", "0", "SciTeX", None),
        HierarchyNode("lower", "4", "Lower-level", "scitex"),
        HierarchyNode("tenth", "4.10", "Tenth", "lower"),
        HierarchyNode("second", "4.2", "Second", "lower"),
    )
    # Act
    result = validate_hierarchy(nodes)
    # Assert
    assert [n.index for n in result] == ["0", "4", "4.2", "4.10"]


def test_breadcrumbs_keep_stable_ids_and_source_labels():
    # Arrange
    nodes = _nodes()
    # Act
    result = hierarchy_breadcrumbs(reversed(nodes), "package:scitex-sdk")
    # Assert
    assert [(n.id, n.label) for n in result] == [
        ("scitex", "SciTeX"),
        ("scitex.applications", "Applications"),
        ("package:scitex-sdk", "SciTeX SDK"),
    ]


def test_unknown_packages_are_not_given_synthetic_breadcrumbs():
    # Arrange
    nodes = _nodes()
    # Act
    # Assert
    with pytest.raises(KeyError, match="package:unassigned"):
        hierarchy_breadcrumbs(nodes, "package:unassigned")


@pytest.mark.parametrize("duplicate", ["id", "index"])
def test_duplicate_ownership_is_refused(duplicate):
    # Arrange
    nodes = _nodes()
    extra = (
        replace(nodes[-1], label="Conflicting SDK owner")
        if duplicate == "id"
        else (
            HierarchyNode(
                "other", "2.5", "Conflicting index owner", "scitex.applications"
            )
        )
    )
    # Act
    # Assert
    with pytest.raises(ValueError, match=f"duplicate hierarchy {duplicate}"):
        validate_hierarchy((*nodes, extra))


@pytest.mark.parametrize("order", [False, True])
def test_missing_ancestors_fail_independently_of_discovery_order(order):
    # Arrange
    nodes = (
        _nodes()[0],
        replace(_nodes()[1], parent_id="missing-layer"),
        _nodes()[2],
    )
    # Act
    # Assert
    with pytest.raises(ValueError, match="missing hierarchy parent: missing-layer"):
        validate_hierarchy(reversed(nodes) if order else nodes)


def test_cycles_are_refused_before_breadcrumb_traversal():
    # Arrange
    nodes = (
        _nodes()[0],
        HierarchyNode("one", "1", "One", "two"),
        HierarchyNode("two", "2", "Two", "one"),
    )
    # Act
    # Assert
    with pytest.raises(ValueError, match="hierarchy cycle"):
        hierarchy_breadcrumbs(nodes, "one")


@pytest.mark.parametrize("index", ["3.5", "2.5.1", "5"])
def test_child_indices_must_extend_their_actual_parent(index):
    # Arrange
    nodes = _nodes()
    # Act
    # Assert
    with pytest.raises(ValueError, match="index does not extend parent"):
        validate_hierarchy((*nodes[:2], replace(nodes[2], index=index)))


@pytest.mark.parametrize(
    "kind", ["empty", "missing", "multiple", "wrong-id", "wrong-index"]
)
def test_only_the_scitex_root_at_zero_can_root_a_complete_tree(kind):
    # Arrange
    nodes = _nodes()
    variants = {
        "empty": (),
        "missing": nodes[1:],
        "multiple": (*nodes, HierarchyNode("other-root", "1", "Other", None)),
        "wrong-id": (replace(nodes[0], id="other"), *nodes[1:]),
        "wrong-index": (replace(nodes[0], index="1"), *nodes[1:]),
    }
    # Act
    # Assert
    with pytest.raises(ValueError, match="one scitex root at index 0"):
        validate_hierarchy(variants[kind])


def test_untyped_provider_records_are_not_silently_coerced():
    # Arrange
    nodes = ({"id": "scitex", "index": "0"},)
    # Act
    # Assert
    with pytest.raises(TypeError, match="HierarchyNode records"):
        validate_hierarchy(nodes)


def test_sdk_provider_declares_only_its_own_assigned_slot():
    # Arrange
    expected = (
        HierarchyNode(
            "package:scitex-sdk",
            "2.5",
            "SciTeX SDK",
            "scitex.applications",
            "scitex-sdk",
        ),
    )
    # Act
    result = get_hierarchy_nodes()
    # Assert
    assert result == expected


def test_isolated_leaf_declaration_does_not_invent_its_missing_parents():
    # Arrange
    declaration = get_hierarchy_nodes()
    # Act
    # Assert
    with pytest.raises(ValueError, match="one scitex root at index 0"):
        validate_hierarchy(declaration)


def test_source_declares_the_sdk_owned_metadata_provider():
    # Arrange
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    # Act
    result = project["entry-points"]["scitex_dev.hierarchy"]
    # Assert
    assert result == {"scitex-sdk": "scitex_sdk.hierarchy:get_hierarchy_nodes"}
