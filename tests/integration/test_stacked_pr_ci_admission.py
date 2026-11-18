"""Actual test workflow admission and retained fork guard execution."""

import subprocess

import pytest
import yaml

from tests._checkout import REPO_ROOT

WORKFLOWS = ("python-package.yml", "frontend.yml")


def workflow(name):
    return yaml.safe_load((REPO_ROOT / ".github/workflows" / name).read_text())


def events(document):
    # PyYAML's YAML1.1 resolver treats GitHub's bare 'on' key as True.
    return document.get("on", document.get(True))


@pytest.mark.parametrize("name", WORKFLOWS)
def test_pull_requests_to_stacked_feature_bases_are_not_filtered_out(name):
    configuration = events(workflow(name))["pull_request"] or {}
    assert "branches" not in configuration
    assert "branches-ignore" not in configuration
    assert "paths" not in configuration
    assert "paths-ignore" not in configuration


@pytest.mark.parametrize("name", WORKFLOWS)
def test_direct_pushes_remain_limited_to_main_and_develop(name):
    assert events(workflow(name))["push"]["branches"] == ["main", "develop"]


@pytest.mark.parametrize("name", WORKFLOWS)
def test_no_privileged_pull_request_target_event_is_added(name):
    assert "pull_request_target" not in events(workflow(name))


@pytest.mark.parametrize("name", WORKFLOWS)
def test_every_execution_job_refuses_forks_before_checkout_or_run(tmp_path, name):
    jobs = workflow(name)["jobs"]
    checked = []
    for job_id, job in jobs.items():
        if "steps" not in job:
            continue  # Reusable runner admission has no repository checkout.
        first = job["steps"][0]
        assert "github.event_name == 'pull_request'" in first["if"]
        assert (
            "github.event.pull_request.head.repo.full_name != github.repository"
            in first["if"]
        )
        assert "uses" not in first
        result = subprocess.run(
            ["bash", "-c", first["run"]],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert result.returncode == 1
        assert "Fork-authored code is not run" in result.stdout
        assert job.get("needs") == "runner-admission"
        checked.append(job_id)
    assert checked
    assert jobs["runner-admission"]["permissions"] == {}
    assert "@" in jobs["runner-admission"]["uses"]
