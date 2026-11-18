"""Bind hierarchy records to the declaring package before tree composition."""

from dataclasses import replace

import pytest

from scitex_sdk.hierarchy import (
    HierarchyNode,
    get_hierarchy_nodes,
    validate_hierarchy,
    validate_hierarchy_provider,
)


def _umbrella():
    return (
        HierarchyNode("scitex", "0", "SciTeX", None),
        HierarchyNode("scitex.applications", "2", "Applications", "scitex"),
        HierarchyNode("scitex.main", "1", "Main", "scitex"),
        HierarchyNode("package:scitex", "1.1", "scitex", "scitex.main", "scitex"),
    )


def test_sdk_leaf_can_declare_itself_without_copying_its_parents():
    # Arrange
    nodes = get_hierarchy_nodes()
    # Act
    result = validate_hierarchy_provider(iter(nodes), distribution="scitex-sdk")
    # Assert
    assert result == nodes


def test_umbrella_can_declare_its_own_package_and_groups_in_numeric_order():
    # Arrange
    nodes = _umbrella()
    # Act
    result = validate_hierarchy_provider(reversed(nodes), distribution="scitex")
    # Assert
    assert [node.index for node in result] == ["0", "1", "1.1", "2"]


@pytest.mark.parametrize("owner", ["scitex-dev", "scitex", "unlisted-package"])
def test_a_provider_cannot_claim_another_packages_record(owner):
    # Arrange
    nodes = get_hierarchy_nodes()
    # Act
    # Assert
    with pytest.raises(ValueError, match=f"provider {owner} cannot declare scitex-sdk"):
        validate_hierarchy_provider(nodes, distribution=owner)


@pytest.mark.parametrize("group", _umbrella()[:3])
def test_leaf_providers_cannot_claim_root_or_group_records(group):
    # Arrange
    nodes = (*get_hierarchy_nodes(), group)
    # Act
    # Assert
    with pytest.raises(ValueError, match="groups belong to scitex"):
        validate_hierarchy_provider(nodes, distribution="scitex-sdk")


@pytest.mark.parametrize("owner", ["scitex-sdk", "scitex"])
def test_an_empty_declaration_cannot_silently_omit_the_owning_package(owner):
    # Arrange
    nodes = ()
    # Act
    # Assert
    with pytest.raises(ValueError, match="must declare its own package"):
        validate_hierarchy_provider(nodes, distribution=owner)


def test_umbrella_groups_alone_are_not_an_umbrella_package_declaration():
    # Arrange
    nodes = _umbrella()[:3]
    # Act
    # Assert
    with pytest.raises(ValueError, match="must declare its own package: scitex"):
        validate_hierarchy_provider(nodes, distribution="scitex")


@pytest.mark.parametrize(
    "owner", ["SciTeX-SDK", "scitex_sdk", "scitex.sdk", "", " x", None, 1]
)
def test_provider_identity_requires_canonical_distribution_spelling(owner):
    # Arrange
    nodes = get_hierarchy_nodes()
    # Act
    # Assert
    with pytest.raises(ValueError, match="hierarchy distribution"):
        validate_hierarchy_provider(nodes, distribution=owner)


def test_plain_dicts_are_not_silently_converted_into_owned_records():
    # Arrange
    nodes = ({"distribution": "scitex-sdk", "id": "package:scitex-sdk"},)
    # Act
    # Assert
    with pytest.raises(TypeError, match="HierarchyNode records"):
        validate_hierarchy_provider(nodes, distribution="scitex-sdk")


def test_duplicate_records_are_refused_before_composition():
    # Arrange
    nodes = get_hierarchy_nodes() * 2
    # Act
    # Assert
    with pytest.raises(ValueError, match="duplicate hierarchy id"):
        validate_hierarchy_provider(nodes, distribution="scitex-sdk")


def test_umbrella_cannot_assign_the_same_index_to_different_records():
    # Arrange
    nodes = _umbrella()
    conflict = replace(nodes[2], index="2")
    # Act
    # Assert
    with pytest.raises(ValueError, match="duplicate hierarchy index"):
        validate_hierarchy_provider(
            (*nodes[:2], conflict, nodes[3]), distribution="scitex"
        )


def test_owned_declarations_still_need_complete_tree_validation():
    # Arrange
    nodes = validate_hierarchy_provider(
        get_hierarchy_nodes(), distribution="scitex-sdk"
    )
    # Act
    # Assert
    with pytest.raises(ValueError, match="one scitex root at index 0"):
        validate_hierarchy(nodes)


def test_admitted_leaf_and_umbrella_records_form_one_shared_tree():
    # Arrange
    root = validate_hierarchy_provider(_umbrella(), distribution="scitex")
    sdk = validate_hierarchy_provider(get_hierarchy_nodes(), distribution="scitex-sdk")
    # Act
    result = validate_hierarchy((*root, *sdk))
    # Assert
    assert [node.id for node in result] == [
        "scitex",
        "scitex.main",
        "package:scitex",
        "scitex.applications",
        "package:scitex-sdk",
    ]
