"""Exercise the actual release verifier on real owned archive members."""

import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

import pytest

from tests._checkout import REPO_ROOT


def _verifier():
    spec = importlib.util.spec_from_file_location(
        "owned_sdk_artifacts", REPO_ROOT / "scripts/verify-artifacts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifacts(tmp_path, document=None, kind=None, broken_package=None):
    source = tmp_path / "source"
    package = source / "src/scitex_sdk"
    package.mkdir(parents=True)
    (source / "pyproject.toml").write_text(
        '[project]\nname="scitex-sdk"\nversion="0.0.0"\n'
    )
    (source / "package.json").write_text('{"version":"0.0.0"}')
    documents = {
        "CLA.md": b"# Owned contributor agreement\n",
        "CONTRIBUTING.md": b"# Owned contribution instructions\n",
    }
    for name, data in documents.items():
        (source / name).write_bytes(data)
    exports = {
        "./package.json": "./package.json",
        "./ui": "./ui/static/scitex_sdk/ui/index.js",
        "./ui/react": "./ui/static/scitex_sdk/ui/react/index.js",
        "./ui/ts": "./ui/static/scitex_sdk/ui/ts/index.ts",
        "./ui/css/*": "./ui/static/scitex_sdk/ui/css/*",
        "./ui/ts/*": "./ui/static/scitex_sdk/ui/ts/*",
    }
    members = {
        "__init__.py": b"# Owned archive control\n",
        "package.json": json.dumps(
            {"name": "@scitex/sdk", "version": "0.0.0", "exports": exports}
        ).encode(),
        "ui/static/scitex_sdk/ui/index.js": b"export {};\n",
        "ui/static/scitex_sdk/ui/react/index.js": b"export {};\n",
        "ui/static/scitex_sdk/ui/ts/index.ts": b"export {};\n",
        "ui/static/scitex_sdk/ui/css/base.css": b"body {}\n",
    }
    for name, data in members.items():
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    wheel = tmp_path / "owned.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in members.items():
            content = (
                b"changed\n"
                if broken_package == "wheel" and name == "__init__.py"
                else data
            )
            archive.writestr("scitex_sdk/" + name, content)
        archive.writestr(
            "scitex_sdk-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scitex-sdk\nVersion: 0.0.0\n",
        )
    sdist = tmp_path / "owned.tar.gz"
    prefix = "scitex_sdk-0.0.0"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, data in members.items():
            content = (
                b"changed\n"
                if broken_package == "sdist" and name == "__init__.py"
                else data
            )
            info = tarfile.TarInfo(prefix + "/src/scitex_sdk/" + name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        for name, data in documents.items():
            if name == document and kind == "missing":
                continue
            path = (
                (
                    "foreign-root"
                    if name == document and kind == "foreign-root"
                    else prefix
                )
                + "/"
                + name
            )
            info = tarfile.TarInfo(path)
            if name == document and kind in {"symlink", "hardlink", "directory"}:
                info.type = {
                    "symlink": tarfile.SYMTYPE,
                    "hardlink": tarfile.LNKTYPE,
                    "directory": tarfile.DIRTYPE,
                }[kind]
                info.linkname = prefix + "/not-a-document"
                archive.addfile(info)
            else:
                content = (
                    b"changed\n" if name == document and kind == "changed" else data
                )
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
                if name == document and kind == "duplicate":
                    archive.addfile(info, io.BytesIO(content))
    return source, wheel, sdist


@pytest.mark.parametrize("document", ["CLA.md", "CONTRIBUTING.md"])
@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "changed",
        "symlink",
        "hardlink",
        "directory",
        "duplicate",
        "foreign-root",
    ],
)
def test_incomplete_or_inexact_community_member_is_refused(tmp_path, document, kind):
    # Arrange
    source, wheel, sdist = _artifacts(tmp_path, document, kind)
    verifier = _verifier()
    # Act
    with pytest.raises(ValueError) as error:
        verifier.verify(source, wheel, sdist)
    # Assert
    assert document in str(error.value)


def test_exact_regular_community_documents_are_accepted(tmp_path):
    # Arrange
    source, wheel, sdist = _artifacts(tmp_path)
    verifier = _verifier()
    # Act
    result = verifier.verify(source, wheel, sdist)
    # Assert
    assert result["version"] == "0.0.0"


@pytest.mark.parametrize("broken_package", ["wheel", "sdist"])
def test_existing_runtime_package_mismatch_is_still_refused(tmp_path, broken_package):
    # Arrange
    source, wheel, sdist = _artifacts(tmp_path, broken_package=broken_package)
    verifier = _verifier()
    # Act
    with pytest.raises(ValueError) as error:
        verifier.verify(source, wheel, sdist)
    # Assert
    assert re.search("source mismatch|package members", str(error.value))


@pytest.mark.parametrize("document", ["CLA.md", "CONTRIBUTING.md"])
def test_release_cli_exits_nonzero_for_missing_document(tmp_path, document):
    # Arrange
    source, wheel, sdist = _artifacts(tmp_path, document, "missing")
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/verify-artifacts.py"),
        "--source",
        str(source),
        "--wheel",
        str(wheel),
        "--sdist",
        str(sdist),
    ]
    # Act
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=10, check=False
    )
    # Assert
    assert (result.returncode, document in result.stderr) == (1, True)
