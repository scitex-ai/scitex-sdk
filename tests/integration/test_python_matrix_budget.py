"""Keep all Python gates while bounding cold-install disk fan-out."""


import pytest
import yaml

from tests._checkout import REPO_ROOT


@pytest.mark.parametrize(
    ("filename", "job"),
    [
        ("python-package.yml", "package"),
        ("pypi-publish-and-github-release-on-tag.yml", "test"),
    ],
)
def test_python_matrices_keep_all_versions_and_one_inflight_leg(filename, job):
    # Arrange
    root = REPO_ROOT
    workflow = yaml.safe_load((root / ".github/workflows" / filename).read_text())
    configured = workflow["jobs"][job]
    strategy = configured["strategy"]
    # Act
    observation = (
        strategy["max-parallel"],
        set(strategy["matrix"]["python-version"]),
        strategy["fail-fast"],
        any("-m pytest tests/" in step.get("run", "") for step in configured["steps"]),
    )
    # Assert
    assert observation == (1, {"3.11", "3.12", "3.13"}, False, True)
