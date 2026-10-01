#!/usr/bin/env python3
"""Validate registered published consumer graphs without publishing or archiving."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from packaging.requirements import Requirement
from packaging.version import Version

REQUIRED_GRAPHS = {
    "sdk-all", "figrecipe-gui", "writer-gui", "hub-gui", "stats-server",
    "scholar-all", "storage-gui", "cards-web", "sac-gui",
    "umbrella-app-ui", "business-core",
    "template-core", "dev-all", "config-core", "clew-gui",
}
NON_SDK_OWNERS = {"template-core", "dev-all", "config-core"}


def validate_policy(policy: dict) -> list[dict]:
    if not isinstance(policy, dict) or type(policy.get("schema")) is not int or policy["schema"] != 1:
        raise ValueError("Retirement policy must be a schema-1 object")
    graphs = policy.get("graphs", [])
    if not isinstance(graphs, list) or not all(isinstance(row, dict) for row in graphs):
        raise ValueError("Retirement graphs must be a list of objects")
    labels = [row.get("name") for row in graphs]
    if not all(isinstance(label, str) for label in labels):
        raise ValueError("Every graph name must be a string")
    if len(labels) != len(set(labels)) or set(labels) != REQUIRED_GRAPHS:
        raise ValueError("Retirement policy must contain every audited consumer graph exactly once")
    unresolved = []
    for row in graphs:
        if not isinstance(row.get("distribution"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", row["distribution"]):
            raise ValueError("Graph root must be a published distribution name")
        if not isinstance(row.get("extras"), list) or not all(
                isinstance(extra, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", extra)
                for extra in row["extras"]):
            raise ValueError("Extras must be literal published extra names")
        expected = "owner" if row["name"] == "sdk-all" else (
            "none" if row["name"] in NON_SDK_OWNERS else "active")
        if row.get("sdk_requirement") != expected:
            raise ValueError("Consumer SDK dependency classification differs from its audited contract")
        if not (row.get("minimum_canonical_version") is None or isinstance(row["minimum_canonical_version"], str)):
            raise ValueError("Canonical release floor must be a version string or an explicit unresolved null")
        if not (row.get("canonical_source_commit") is None or isinstance(row["canonical_source_commit"], str)):
            raise ValueError("Canonical source commit must be a string or an explicit unresolved null")
        if not row.get("minimum_canonical_version") or not row.get("canonical_source_commit"):
            unresolved.append(row["name"])
            continue
        version = Version(row["minimum_canonical_version"])
        if version.is_devrelease or version.is_prerelease or version.local:
            raise ValueError("Canonical consumer floor must be a genuine final published release")
        if not re.fullmatch(r"[0-9a-f]{40}", row["canonical_source_commit"]):
            raise ValueError("Canonical source commit must be a complete immutable Git SHA")
        Requirement(row["distribution"])
    if unresolved:
        raise ValueError("DEPENDENCY RETIREMENT NOT READY: genuine canonical release floors/source commits unregistered: " + ", ".join(sorted(unresolved)))
    return graphs


def requires_canonical_sdk(metadata: dict, extras: list[str]) -> bool:
    for text in metadata.get("requires_dist", []):
        requirement = Requirement(text)
        if requirement.name.lower().replace("_", "-") != "scitex-sdk":
            continue
        if requirement.marker and not any(requirement.marker.evaluate({"extra": extra}) for extra in ["", *extras]):
            continue
        for specifier in requirement.specifier:
            if specifier.operator in {">=", ">", "~=", "=="}:
                value = specifier.version.removesuffix(".*")
                if Version(value) >= Version("0.3.0"):
                    return True
    return False


def run_graph(row: dict, scratch: Path) -> dict:
    graph = scratch / row["name"]
    graph.mkdir()
    python = graph / "venv/bin/python"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("SCITEX_", "PG", "PIP_", "UV_", "COVERAGE_"))
           and key not in {"DATABASE_URL", "DJANGO_SETTINGS_MODULE", "PYTHONPATH", "VIRTUAL_ENV", "GH_TOKEN", "GITHUB_TOKEN"}
           and not re.search(r"(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|PASSWORD)$", key)}
    env.update({"SCITEX_DIR": str(graph / "scitex"), "TMPDIR": str(graph / "tmp"),
                "XDG_CACHE_HOME": str(graph / "cache"), "PIP_CACHE_DIR": str(graph / "cache/pip"),
                "PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    (graph / "tmp").mkdir()
    commands = [[sys.executable, "-m", "venv", str(graph / "venv")]]
    extras = row.get("extras", [])
    requirement = row["distribution"] + ("[" + ",".join(extras) + "]" if extras else "") + "==" + row["minimum_canonical_version"]
    commands += [[str(python), "-m", "pip", "install", "--index-url", "https://pypi.org/simple", requirement],
                 [str(python), "-m", "pip", "check"],
                 [str(python), str(Path(__file__).with_name("ownership_gate.py")), "--mode", "retirement",
                  "--graph", row["name"], "--sdk-requirement", row["sdk_requirement"],
                  "--output", str(graph / "ownership.json")]]
    for index, command in enumerate(commands):
        result = subprocess.run(command, env=env, cwd=graph, capture_output=True, text=True)
        (graph / f"phase-{index}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            return {"graph": row["name"], "status": "BLOCKED", "phase": index,
                    "exit_code": result.returncode, "evidence": str(graph)}
    # Inspect root declaration rather than letting a sibling graph provide a
    # newer SDK and mask the consumer's own missing API floor.
    probe = subprocess.run([str(python), "-c",
                            "import importlib.metadata as m,json,sys;d=m.metadata(sys.argv[1]);print(json.dumps({'version':d['Version'],'requires_dist':d.get_all('Requires-Dist',[]),'provides_extra':d.get_all('Provides-Extra',[])}))",
                            row["distribution"]], env=env, capture_output=True, text=True)
    (graph / "root-metadata.log").write_text(probe.stdout + probe.stderr)
    if probe.returncode:
        return {"graph": row["name"], "status": "BLOCKED", "phase": "root-metadata", "exit_code": probe.returncode}
    metadata = json.loads(probe.stdout)
    if set(extras) - set(metadata["provides_extra"]):
        return {"graph": row["name"], "status": "BLOCKED", "phase": "missing-declared-extra",
                "detail": "Requested runtime group does not exist in the published root metadata"}
    if row["sdk_requirement"] == "active" and not requires_canonical_sdk(metadata, extras):
        return {"graph": row["name"], "status": "BLOCKED", "phase": "consumer-sdk-floor",
                    "detail": "Required consumer does not declare active SDK>=0.3.0"}
    return {"graph": row["name"], "status": "PASSED", "installed_root_version": metadata["version"],
            "registered_source_commit": row["canonical_source_commit"],
            "source_association": "reviewed policy registration; resolver does not attest Git provenance",
            "evidence": str(graph)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        graphs = validate_policy(json.loads(args.policy.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"status": "RETIREMENT_POLICY_BLOCKED", "dependency_retirement_ready": False, "reason": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(report["reason"])
        return 1
    # Reusing a resolved environment could hide a missing owner or dependency.
    args.scratch.mkdir(parents=True, exist_ok=False)
    results = [run_graph(row, args.scratch) for row in graphs]
    passed = all(row["status"] == "PASSED" for row in results)
    report = {"status": "RETIREMENT_DEPENDENCY_GATES_PASSED" if passed else "RETIREMENT_BLOCKED",
              "dependency_retirement_ready": False,
              "repository_archive": "separate administrative state; not dependency/install evidence",
              "remaining_gates": "source/native GUI/frontend behavior and registered artifact provenance require owning review",
              "graphs": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
