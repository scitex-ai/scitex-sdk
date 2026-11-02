"""Execute the actual release resolver shell with hostile inputs as data."""
import os
from pathlib import Path
import re
import subprocess

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/pypi-publish-and-github-release-on-tag.yml"


def resolver_scripts():
    source = WORKFLOW.read_text()
    blocks = re.findall(r"      - name: Resolve version\n(.*?)(?=      - )", source, re.S)
    if len(blocks) != 2:
        raise AssertionError("both actual test and build resolvers must be covered")
    return ["\n".join(line[10:] for line in block.split("        run: |\n", 1)[1].splitlines()) for block in blocks]


def test_actual_resolvers_select_push_and_manual_tags(tmp_path):
    outputs = []
    for index, script in enumerate(resolver_scripts()):
        for event in ("push", "workflow_dispatch"):
            output = tmp_path / f"{index}-{event}"
            env = dict(os.environ, GITHUB_EVENT_NAME=event, GITHUB_REF="refs/tags/v0.3.18",
                       SDK_MANUAL_RELEASE_TAG="v0.3.18", GITHUB_OUTPUT=str(output))
            child = subprocess.run(["bash", "-c", script], env=env, capture_output=True, timeout=5)
            if child.returncode:
                raise AssertionError(child.stderr)
            outputs.append(output.read_text())
    assert outputs == ["version=v0.3.18\n"] * 4


def test_actual_resolvers_refuse_shell_injection_and_invalid_tags(tmp_path):
    marker = tmp_path / "must-not-exist"
    refused = []
    malicious = [f'v0.3.18"; touch {marker}; #', f"$(touch {marker})", f"`touch {marker}`", "v0.3.18\nversion=v9.9.9", "main", "v0.3.18rc1"]
    for index, script in enumerate(resolver_scripts()):
        for value in malicious:
            output = tmp_path / f"refused-{index}"
            env = dict(os.environ, GITHUB_EVENT_NAME="workflow_dispatch", GITHUB_REF="refs/heads/main",
                       SDK_MANUAL_RELEASE_TAG=value, GITHUB_OUTPUT=str(output))
            child = subprocess.run(["bash", "-c", script], env=env, capture_output=True, timeout=5)
            refused.append(child.returncode != 0 and not output.exists() and not marker.exists())
    assert all(refused)
