#!/usr/bin/env python3
"""Report bootstrap ownership or reject retired owners in one installed graph."""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re

RETIRED_DISTS = {"scitex-app", "scitex-ui"}
RETIRED_MODULES = {"scitex_app", "scitex_ui"}
NON_SDK_GRAPHS = {"config-core", "template-core", "dev-all"}
MODULE_SETTINGS = {
    "INSTALLED_APPS", "MIDDLEWARE", "ROOT_URLCONF",
    "AUTHENTICATION_BACKENDS", "STATICFILES_FINDERS",
}
FRONTEND_TOKEN = re.compile(
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)"
    r"|(?P<string>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
    r"|(?P<template>`(?:\\.|[^`\\])*`)"
    r"|(?P<identifier>[A-Za-z_$][\w$]*)|(?P<punctuation>[^\s])"
)


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def retired_module(value: str) -> bool:
    return value.split(".", 1)[0] in RETIRED_MODULES


def python_imports(text: str) -> list[dict]:
    """Read executable import/settings contexts; preserve labels, FKs and tags."""
    tree = ast.parse(text)
    found = []
    for node in ast.walk(tree):
        references = []
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr == "modules" and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "sys" and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            references = [node.slice.value]
        elif isinstance(node, ast.Import):
            references = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            references = [node.module or ""] if not node.level else []
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name in {"__import__", "import_module", "include"} and node.args:
                value = node.args[0]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    references = [value.value]
            for keyword in node.keywords:
                if keyword.arg in MODULE_SETTINGS:
                    references.extend(value.value for value in ast.walk(keyword.value)
                                      if isinstance(value, ast.Constant) and isinstance(value.value, str))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id in MODULE_SETTINGS for target in targets):
                references = [value.value for value in ast.walk(node.value)
                              if isinstance(value, ast.Constant) and isinstance(value.value, str)]
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in MODULE_SETTINGS | {"context_processors"}:
                    references.extend(item.value for item in ast.walk(value)
                                      if isinstance(item, ast.Constant) and isinstance(item.value, str))
        for reference in references:
            if retired_module(reference):
                found.append({"line": node.lineno, "reference": reference, "kind": "python"})
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(
            getattr(base, "id", getattr(base, "attr", "")) == "AppConfig"
            for base in node.bases
        ):
            for assignment in node.body:
                if (isinstance(assignment, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "name"
                                for target in assignment.targets)
                        and isinstance(assignment.value, ast.Constant)
                        and isinstance(assignment.value.value, str)
                        and retired_module(assignment.value.value)):
                    found.append({"line": assignment.lineno,
                                  "reference": assignment.value.value,
                                  "kind": "django-app-config"})
    return found


def frontend_imports(text: str) -> list[dict]:
    """Read literal static/from/dynamic imports, excluding prose and comments.

    Computed imports and template expressions require the owning source/native
    frontend checks; this packaged static inventory does not execute JavaScript.
    """
    tokens = [match for match in FRONTEND_TOKEN.finditer(text)
              if match.lastgroup not in {"comment", "template"}]
    found = []
    for index, token in enumerate(tokens):
        if token.lastgroup != "string":
            continue
        previous = [item.group() for item in tokens[max(0, index - 2):index]]
        imported = (previous and previous[-1] in {"from", "import"}) or (
            len(previous) == 2 and previous[0] in {"import", "require"} and previous[1] == "("
        )
        reference = token.group()[1:-1]
        if imported and re.match(r"^(?:@scitex/(?:app|ui)|scitex-(?:app|ui))(?:/|$)", reference):
            found.append({"line": text.count("\n", 0, token.start()) + 1,
                          "reference": reference, "kind": "frontend"})
    return found


def file_imports(path: Path) -> list[dict]:
    if path.suffix == ".py":
        return python_imports(path.read_text(encoding="utf-8"))
    if path.suffix in {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}:
        return frontend_imports(path.read_text(encoding="utf-8"))
    if path.name == "package.json":
        manifest = json.loads(path.read_text())
        sections = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
        if not isinstance(manifest, dict) or any(
                not isinstance(manifest.get(section, {}), dict) for section in sections):
            raise ValueError("frontend dependency manifest must contain dependency objects")
        return [{"line": 1, "reference": dependency, "kind": "npm-dependency"}
                for section in sections
                for dependency in manifest.get(section, {})
                if dependency in {"@scitex/app", "@scitex/ui", "scitex-app", "scitex-ui"}]
    return []


def observe() -> dict:
    distributions = list(importlib.metadata.distributions())
    by_name = {normalized(dist.metadata["Name"]): dist for dist in distributions
               if dist.metadata.get("Name")}
    names = [normalized(dist.metadata["Name"]) for dist in distributions if dist.metadata.get("Name")]
    direct_errors = []
    sdk = by_name.get("scitex-sdk")
    if sdk is not None:
        for requirement in sdk.requires or []:
            dependency = re.match(r"[A-Za-z0-9_.-]+", requirement)
            if dependency and normalized(dependency.group()) in RETIRED_DISTS:
                direct_errors.append("SDK directly requires a retired distribution: " + requirement)
    references = []
    unreadable = [{"distribution": name, "detail": "duplicate installed distribution metadata"}
                  for name in sorted(set(names)) if names.count(name) > 1]
    for name, dist in sorted(by_name.items()):
        for entrypoint in dist.entry_points:
            target = entrypoint.value.partition(":")[0].strip()
            if retired_module(target):
                references.append({"distribution": name, "member": "entry_points.txt", "line": 0,
                                   "reference": target, "kind": "entry-point",
                                   "group": entrypoint.group, "name": entrypoint.name})
        if dist.files is None:
            unreadable.append({"distribution": name, "detail": "installed file inventory is missing"})
            continue
        for member in dist.files:
            if member.parts[0].startswith(("..", ".")) or member.suffix not in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json"}:
                continue
            if any(part in {"_docs", "_skills", "tests", "__pycache__"} for part in member.parts):
                continue
            if member.parts[0] in RETIRED_MODULES:
                references.append({"distribution": name, "member": str(member),
                                   "line": 0, "reference": member.parts[0],
                                   "kind": "top-level-package"})
            path = Path(dist.locate_file(member))
            try:
                findings = file_imports(path)
            except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
                unreadable.append({"distribution": name, "member": str(member), "detail": type(exc).__name__ + ": " + str(exc)})
                continue
            for finding in findings:
                references.append({"distribution": name, "member": str(member), **finding})
    modules = []
    for name in sorted(RETIRED_MODULES):
        spec = importlib.util.find_spec(name)
        if spec is not None:
            modules.append({"module": name, "origin": spec.origin,
                            "locations": list(spec.submodule_search_locations or [])})
    for failure in unreadable:
        if failure["distribution"] == "scitex-sdk":
            direct_errors.append("SDK execution inventory is unreadable: " + failure["detail"])
    for reference in references:
        if reference["distribution"] == "scitex-sdk":
            direct_errors.append("SDK contains a retired import: " + reference["member"])
    return {
        "installed_versions": {name: dist.version for name, dist in sorted(by_name.items())},
        "retired_distributions": sorted(RETIRED_DISTS & by_name.keys()),
        "retired_module_specs": modules,
        "retired_import_references": references,
        "unreadable_execution_files": unreadable,
        "direct_sdk_ownership_errors": sorted(set(direct_errors)),
    }


def sdk_is_required(mode: str, graph: str, sdk_requirement: str) -> bool:
    if sdk_requirement not in {"owner", "active", "none"}:
        raise ValueError("Unknown consumer SDK dependency classification")
    if (mode == "bootstrap-observation" or graph == "sdk-all") and sdk_requirement != "owner":
        raise ValueError("SDK bootstrap and sdk-all require the SDK owner classification")
    if sdk_requirement == "none" and graph not in NON_SDK_GRAPHS:
        raise ValueError("Only audited config-core/template-core/dev-all graphs may omit SDK")
    return sdk_requirement != "none"


def evaluate(
    observation: dict, mode: str, graph: str, *, sdk_requirement: str = "owner"
) -> tuple[dict, int]:
    # Only audited non-SDK roots may omit SDK. If it is present, observe()
    # still inspects every SDK edge/member. Bootstrap always requires SDK.
    sdk_required = sdk_is_required(mode, graph, sdk_requirement)
    direct = list(observation["direct_sdk_ownership_errors"])
    if sdk_required and "scitex-sdk" not in observation["installed_versions"]:
        direct.append("scitex-sdk is not installed")
    direct = sorted(set(direct))
    blocked = (direct or observation["retired_distributions"]
               or observation["retired_module_specs"]
               or observation["retired_import_references"]
               or observation["unreadable_execution_files"])
    if mode == "bootstrap-observation":
        status = "SDK_DIRECT_OWNERSHIP_BLOCKED" if direct else "DEPENDENCY_RETIREMENT_NOT_READY"
        exit_code = 1 if direct else 0
    else:
        status = "RETIREMENT_GRAPH_BLOCKED" if blocked else "RETIREMENT_GRAPH_PASSED"
        exit_code = 1 if blocked else 0
    return {"mode": mode, "graph": graph, "status": status,
            "dependency_retirement_ready": False,
            "repository_archive": "separate repository administration; not migration/install evidence",
            "scope": "installed distribution metadata and packaged execution imports; one graph only",
            "normal_resolution": "caller must run normal pip install and pip check before this observation",
            **observation, "sdk_requirement": sdk_requirement,
            "sdk_required": sdk_required,
            "direct_sdk_ownership_errors": direct}, exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("bootstrap-observation", "retirement"), default="retirement")
    parser.add_argument("--graph", required=True)
    parser.add_argument("--sdk-requirement", choices=("owner", "active", "none"), default="owner")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        sdk_is_required(args.mode, args.graph, args.sdk_requirement)
    except ValueError as exc:
        parser.error(str(exc))
    report, code = evaluate(observe(), args.mode, args.graph, sdk_requirement=args.sdk_requirement)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
