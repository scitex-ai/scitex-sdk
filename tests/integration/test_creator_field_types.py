"""Creator JSON refusal and existing-file preservation through real requests."""

import json

import pytest
from django.test import Client


@pytest.mark.parametrize("endpoint", ["/api/validate-input", "/api/create"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("label", 7),
        ("label", True),
        ("description", 7),
        ("description", ["brief"]),
        ("starter", ["blank"]),
        ("starter", {"key": "blank"}),
    ],
)
def test_creator_refuses_nontext_brief_fields(endpoint, field, value, tmp_path):
    # Arrange
    target = tmp_path / "unused"
    payload = {
        "label": "Typed App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": str(target),
        field: value,
    }
    client = Client(raise_request_exception=False)
    # Act
    response = client.post(endpoint, payload, content_type="application/json")
    # Assert
    assert (response.status_code, target.exists()) == (400, False)


@pytest.mark.parametrize("overwrite", ["false", "true", 1, [True]])
def test_creator_refuses_nonboolean_overwrite_without_changes(overwrite, tmp_path):
    # Arrange
    target = tmp_path / "existing"
    target.mkdir()
    marker = target / "AGENTS.md"
    marker.write_text("Keep these existing instructions.\n")
    payload = {
        "label": "Typed App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": str(target),
        "overwrite": overwrite,
    }
    client = Client(raise_request_exception=False)
    # Act
    response = client.post("/api/create", payload, content_type="application/json")
    # Assert
    assert (
        response.status_code,
        marker.read_text(),
        sorted(p.name for p in target.iterdir()),
    ) == (400, "Keep these existing instructions.\n", ["AGENTS.md"])


@pytest.mark.parametrize("target", [7, True, ["directory"], {"path": "directory"}])
def test_creator_refuses_nontext_target(target):
    # Arrange
    client = Client(raise_request_exception=False)
    payload = {
        "label": "Typed App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": target,
    }
    # Act
    response = client.post("/api/create", payload, content_type="application/json")
    # Assert
    assert response.status_code == 400


@pytest.mark.parametrize("overwrite", [False, None])
def test_creator_keeps_false_or_null_overwrite_refusal(overwrite, tmp_path):
    # Arrange
    marker = tmp_path / "AGENTS.md"
    marker.write_text("Keep these existing instructions.\n")
    payload = {
        "label": "Typed App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": str(tmp_path),
        "overwrite": overwrite,
    }
    # Act
    response = Client().post("/api/create", payload, content_type="application/json")
    # Assert
    assert (response.status_code, marker.read_text()) == (
        400,
        "Keep these existing instructions.\n",
    )


def test_creator_keeps_explicit_boolean_overwrite(tmp_path):
    # Arrange
    target = tmp_path / "existing"
    target.mkdir()
    (target / "AGENTS.md").write_text("Owned placeholder.\n")
    payload = {
        "label": "Typed App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": str(target),
        "overwrite": True,
    }
    # Act
    response = Client().post("/api/create", payload, content_type="application/json")
    # Assert
    assert (response.status_code, json.loads(response.content)["success"]) == (
        200,
        True,
    )


def test_creator_keeps_null_optional_description(tmp_path):
    # Arrange
    payload = {
        "label": "Typed App",
        "description": None,
        "starter": "blank",
        "target_dir": str(tmp_path / "created"),
    }
    # Act
    response = Client().post("/api/create", payload, content_type="application/json")
    # Assert
    assert (response.status_code, json.loads(response.content)["success"]) == (
        200,
        True,
    )
