"""Real target errors refuse creation without damaging owned files or aliases."""

import json
import os

import pytest
from django.test import Client


def _state(root):
    return (
        (root / "marker.txt").read_text(),
        sorted(p.name for p in root.iterdir()),
        {p.name: os.readlink(p) for p in root.iterdir() if p.is_symlink()},
    )


@pytest.fixture(params=["file", "file_alias", "dangling_alias", "nul"])
def invalid_target(request, tmp_path):
    marker = tmp_path / "marker.txt"
    marker.write_text("Existing owned data.\n")
    target = tmp_path / "destination"
    if request.param == "file":
        target = marker
    elif request.param == "file_alias":
        target.symlink_to(marker)
    elif request.param == "dangling_alias":
        target.symlink_to(tmp_path / "absent")
    else:
        target = tmp_path / "bad\x00name"
    return str(target), tmp_path


@pytest.mark.parametrize("overwrite", [False, True])
def test_creator_refuses_invalid_target_without_changes(invalid_target, overwrite):
    # Arrange
    target, root = invalid_target
    before = _state(root)
    payload = {
        "label": "Target App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": target,
        "overwrite": overwrite,
    }
    client = Client(raise_request_exception=False)
    # Act
    response = client.post("/api/create", payload, content_type="application/json")
    # Assert
    assert (response.status_code, _state(root)) == (400, before)


def test_creator_preserves_valid_directory_alias(tmp_path):
    # Arrange
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    payload = {
        "label": "Alias App",
        "description": "Record samples",
        "starter": "blank",
        "target_dir": str(alias),
    }
    # Act
    response = Client().post("/api/create", payload, content_type="application/json")
    # Assert
    assert (
        response.status_code,
        json.loads(response.content)["success"],
        alias.is_symlink(),
        (real / "AGENTS.md").is_file(),
    ) == (200, True, True, True)
