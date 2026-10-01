"""Verify SDK source, sdist, wheel, and frontend package identity before release."""

from __future__ import annotations

import argparse
import json
from email.parser import BytesParser
from pathlib import Path
import re
import tarfile
import tomllib
import zipfile


def verify(source: Path, wheel: Path, sdist: Path, tag: str | None = None) -> dict:
    project = tomllib.loads((source / "pyproject.toml").read_text())["project"]
    version = project["version"]
    if tag is not None and tag != f"v{version}":
        raise ValueError("release tag does not match SDK source version")
    package = source / "src" / "scitex_sdk"
    expected = {
        str(path.relative_to(package)): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    if not expected:
        raise ValueError("SDK source package is empty")
    with zipfile.ZipFile(wheel) as archive:
        actual = {
            name.removeprefix("scitex_sdk/"): archive.read(name)
            for name in archive.namelist()
            if name.startswith("scitex_sdk/") and not name.endswith("/")
        }
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError("wheel must have exactly one distribution metadata file")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        if metadata["Name"] != "scitex-sdk" or metadata["Version"] != version:
            raise ValueError("wheel distribution identity differs from source")
        for requirement in metadata.get_all("Requires-Dist", []):
            match = re.match(r"[A-Za-z0-9_.-]+", requirement)
            if match is None:
                raise ValueError("invalid distribution dependency metadata")
            dependency = match.group()
            if dependency.lower().replace("_", "-") in {"scitex-app", "scitex-ui"}:
                raise ValueError("wheel still depends on a retired distribution")
        foreign = [
            name for name in archive.namelist()
            if name.startswith(("scitex_app/", "scitex_ui/"))
        ]
        if foreign:
            raise ValueError("wheel contains a legacy top-level package")
    if expected != actual:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        changed = sorted(key for key in expected.keys() & actual.keys()
                         if expected[key] != actual[key])
        raise ValueError(f"wheel source mismatch: missing={missing}, extra={extra}, changed={changed}")
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        actual_sdist = {}
        for member in members:
            parts = Path(member.name).parts
            if member.isfile() and len(parts) > 3 and parts[1:3] == ("src", "scitex_sdk"):
                file = archive.extractfile(member)
                assert file is not None
                actual_sdist[str(Path(*parts[3:]))] = file.read()
    if expected != actual_sdist:
        raise ValueError("sdist package members or bytes differ from source")
    frontend = json.loads(expected["package.json"])
    tooling = json.loads((source / "package.json").read_text())
    if frontend["name"] != "@scitex/sdk" or frontend["version"] != version:
        raise ValueError("frontend package identity differs from SDK")
    if tooling["version"] != version:
        raise ValueError("frontend tooling version differs from SDK")
    exports = frontend["exports"]
    for entry in ("./ui", "./ui/react", "./ui/ts", "./ui/css/*", "./ui/ts/*"):
        if entry not in exports:
            raise ValueError(f"missing frontend export: {entry}")
    for entry, target in exports.items():
        if entry == "./package.json":
            if target != "./package.json":
                raise ValueError("frontend manifest export points elsewhere")
            continue
        if (not entry.startswith("./ui")
                or not target.startswith("./ui/static/scitex_sdk/ui/")
                or ".." in Path(target).parts
                or "\\" in target):
            raise ValueError("frontend export leaves the owning UI asset directory")
        if not list(package.glob(target.removeprefix("./"))):
            raise ValueError(f"frontend export has no packaged target: {entry}")
    return {"version": version, "package_members": len(expected), "frontend_exports": len(exports)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--tag")
    args = parser.parse_args()
    print(json.dumps(verify(args.source, args.wheel, args.sdist, args.tag), sort_keys=True))
