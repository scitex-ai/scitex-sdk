"""Project real installed hierarchy resources without loading provider code."""

import json
import sys
from importlib import invalidate_caches

import pytest

from scitex_sdk.app.package_navigation import build_package_navigation


def _catalog():
    return {"schema_version": 1, "root": "owned", "nodes": [
        {"id": "owned", "label": "Owned", "index": "0", "parent_id": None, "kind": "root"},
        {"id": "apps", "label": "Apps", "index": "2", "parent_id": "owned", "kind": "group"},
        {"id": "leaf", "label": "Leaf", "index": "2.10", "parent_id": "apps", "kind": "package", "distribution": "owned-leaf"},
        {"id": "peer", "label": "Peer", "index": "2.2", "parent_id": "apps", "kind": "package", "distribution": "owned-peer"},
    ]}


@pytest.fixture
def hierarchy(tmp_path):
    package = tmp_path / "sdk_owned_hierarchy_fixture"
    package.mkdir()
    (package / "__init__.py").write_text("raise RuntimeError('provider must never import')\n")
    resource = package / "_package_hierarchy.json"
    resource.write_text(json.dumps(_catalog()))
    info = tmp_path / "owned_sdk_hierarchy-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned-sdk-hierarchy\nVersion: 1.0\n")
    (info / "entry_points.txt").write_text("[scitex_dev.hierarchy]\nowned = sdk_owned_hierarchy_fixture\n")
    sys.path.insert(0, str(tmp_path))
    invalidate_caches()
    yield tmp_path, resource
    sys.path.remove(str(tmp_path))
    invalidate_caches()


def test_indices_breadcrumbs_and_provider_non_execution(hierarchy):
    # Arrange
    metadata, _ = hierarchy
    # Act
    result = build_package_navigation(["Owned_Leaf"], metadata_path=[metadata])
    row = result["packages"][0]
    # Assert
    assert (row, "sdk_owned_hierarchy_fixture" in sys.modules) == ({
        "distribution": "owned-leaf", "state": "indexed", "node_id": "leaf",
        "root_id": "owned", "index": "2.10", "breadcrumbs": [
            {"id": "owned", "index": "0", "label": "Owned", "kind": "root"},
            {"id": "apps", "index": "2", "label": "Apps", "kind": "group"},
            {"id": "leaf", "index": "2.10", "label": "Leaf", "kind": "package"},
        ],
    }, False)


def test_unselected_allocations_are_pruned(hierarchy):
    # Arrange
    metadata, _ = hierarchy
    # Act
    result = build_package_navigation(["owned-leaf"], metadata_path=[metadata])
    tree = result["trees"][0]
    # Assert
    assert (tree["id"], [node["id"] for node in tree["children"][0]["children"]]) == ("owned", ["leaf"])


def test_unindexed_packages_have_no_invented_parent_or_position(hierarchy):
    # Arrange
    metadata, _ = hierarchy
    # Act
    result = build_package_navigation(["other-package"], metadata_path=[metadata])
    # Assert
    assert (result["trees"], result["unindexed"], result["packages"]) == ([], ["other-package"], [{
        "distribution": "other-package", "state": "unindexed", "node_id": None,
        "root_id": None, "index": None, "breadcrumbs": [],
    }])


def test_package_order_is_numeric_and_independent_of_input_order(hierarchy):
    # Arrange
    metadata, _ = hierarchy
    # Act
    result = build_package_navigation(["owned-leaf", "owned-peer", "owned-leaf"], metadata_path=[metadata])
    # Assert
    assert [row["distribution"] for row in result["packages"]] == ["owned-peer", "owned-leaf"]


def test_empty_metadata_does_not_fabricate_a_catalog(tmp_path):
    # Arrange
    selected = ["owned-leaf"]
    # Act
    result = build_package_navigation(selected, metadata_path=[tmp_path])
    # Assert
    assert (result["trees"], result["unindexed"], result["declarations_only"], result["live_verified"]) == ([], selected, True, False)


def test_invalid_hierarchy_is_not_replaced_by_a_fallback(hierarchy):
    # Arrange
    metadata, resource = hierarchy
    resource.write_text('{"schema_version":1,"root":"owned","nodes":[]}')
    # Act
    # Assert
    with pytest.raises(ValueError, match="1 to 10000"):
        build_package_navigation(["owned-leaf"], metadata_path=[metadata])


@pytest.mark.parametrize("owner", ["../secret", " invalid", "", "A\n"])
def test_invalid_selected_package_is_rejected(owner, tmp_path):
    # Arrange
    selected = [owner]
    # Act
    # Assert
    with pytest.raises(ValueError):
        build_package_navigation(selected, metadata_path=[tmp_path])
