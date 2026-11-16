"""Bundled-resource names agree with the real existing CLI and MCP surfaces."""

import json

import pytest
from click.testing import CliRunner

from scitex_sdk import list_bundled_skills


@pytest.mark.parametrize("component", ["app", "ui"])
def test_bundled_names_match_existing_cli_list(component):
    # Arrange
    from scitex_sdk.cli import main

    expected = list_bundled_skills()["scitex-" + component]
    # Act
    result = CliRunner().invoke(main, [component, "dev", "skills", "list", "--json"])
    observed = sorted(row["name"] for row in json.loads(result.output))
    # Assert
    assert (result.exit_code, observed) == (0, expected)


@pytest.mark.parametrize("component", ["app", "ui"])
def test_bundled_names_match_existing_mcp_list(component):
    # Arrange
    import importlib

    module = importlib.import_module("scitex_sdk." + component + "._mcp.server")
    tool = getattr(module, component + "_skills_list")
    expected = list_bundled_skills()["scitex-" + component]
    # Act
    result = json.loads(tool())
    # Assert
    assert (result["success"], result["skills"]) == (True, expected)


def test_public_helper_reads_no_user_state_or_optional_framework(tmp_path):
    # Arrange
    import os
    import subprocess
    import sys

    home = tmp_path / "user-state"
    home.mkdir()
    environment = dict(
        os.environ,
        HOME=str(home),
        SCITEX_DIR=str(home / ".scitex"),
        XDG_CACHE_HOME=str(home / ".cache"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    program = (
        "import json,sys;from scitex_sdk import list_bundled_skills;"
        "import scitex_sdk._web._api,scitex_sdk._web._views;"
        'print(json.dumps({"namespaces":sorted(list_bundled_skills()),'
        '"optional_loaded":any(n.startswith(("django","fastmcp")) for n in sys.modules)}))'
    )
    # Act
    result = subprocess.run(
        [sys.executable, "-I", "-c", program],
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    observed = json.loads(result.stdout)
    # Assert
    assert (observed, list(home.rglob("*"))) == (
        {
            "namespaces": ["scitex-app", "scitex-sdk", "scitex-ui"],
            "optional_loaded": False,
        },
        [],
    )


def test_bundled_sdk_names_match_existing_root_cli_catalog():
    # Arrange
    from scitex_sdk.cli import main

    expected = list_bundled_skills()["scitex-sdk"]
    # Act
    result = CliRunner().invoke(main, ["skills", "list", "--json"])
    rows = json.loads(result.output)["scitex-sdk"]
    observed = sorted(
        row["rel_path"][:-3] for row in rows if row["rel_path"] != "SKILL.md"
    )
    # Assert
    assert (result.exit_code, observed) == (0, expected)


@pytest.fixture(
    params=[
        ("app", "absolute"),
        ("app", "relative"),
        ("ui", "absolute"),
        ("ui", "relative"),
    ]
)
def outside_skill_response(request, tmp_path):
    import asyncio
    import importlib
    import os
    from pathlib import Path

    from fastmcp import Client

    component, syntax = request.param
    module = importlib.import_module("scitex_sdk." + component + "._mcp.server")
    marker = tmp_path / "outside-owned-fixture.md"
    marker.write_text("This private fixture is outside the bundled skill tree.")
    root = Path(module.__file__).parent.parent / "_skills" / ("scitex-" + component)
    name = (
        str(marker.with_suffix(""))
        if syntax == "absolute"
        else os.path.relpath(marker.with_suffix(""), root)
    )

    async def exercise():
        async with Client(module.mcp) as client:
            result = await client.call_tool(component + "_skills_get", {"name": name})
            return json.loads(result.content[0].text)

    return asyncio.run(exercise())


def test_mcp_rejects_outside_skill_path(outside_skill_response):
    # Arrange
    response = outside_skill_response
    # Act
    success = response["success"]
    # Assert
    assert success is False


def test_mcp_returns_no_outside_skill_content(outside_skill_response):
    # Arrange
    response = outside_skill_response
    # Act
    leaked = "content" in response
    # Assert
    assert leaked is False


@pytest.mark.parametrize("namespace", ["scitex-sdk", "scitex-app", "scitex-ui"])
def test_every_catalog_page_remains_readable(namespace):
    # Arrange
    from scitex_sdk._bundled_skills import read_bundled_skill

    names = list_bundled_skills()[namespace]
    # Act
    contents = [read_bundled_skill(namespace, name) for name in names]
    # Assert
    assert contents and all(content.strip() for content in contents)


@pytest.mark.parametrize("namespace", ["scitex-sdk", "scitex-app", "scitex-ui"])
def test_bundled_namespace_overview_remains_readable(namespace):
    # Arrange
    from scitex_sdk._bundled_skills import read_bundled_skill

    # Act
    content = read_bundled_skill(namespace, "SKILL")
    # Assert
    assert content.strip()


@pytest.mark.parametrize(
    "name",
    [
        "",
        "../outside",
        "/absolute",
        r"..\outside",
        r"C:\outside",
        "a/../outside",
        "a//b",
        "./outside",
        "null\x00byte",
    ],
)
def test_bundled_reader_rejects_invalid_identifiers(name):
    # Arrange
    from scitex_sdk._bundled_skills import read_bundled_skill

    # Act
    # Assert
    with pytest.raises(ValueError):
        read_bundled_skill("scitex-app", name)


@pytest.fixture(params=["page", "namespace"])
def resource_alias_command(request, tmp_path):
    alias_kind = request.param
    import shutil
    import sys
    from pathlib import Path

    import scitex_sdk

    source = Path(scitex_sdk.__file__).parent
    package = tmp_path / "scitex_sdk"
    package.mkdir()
    for name in ["__init__.py", "_bundled_skills.py"]:
        shutil.copyfile(source / name, package / name)
    for relative in ["_skills", "app/_skills", "ui/_skills"]:
        shutil.copytree(source / relative, package / relative)
    root = package / "app/_skills/scitex-app"
    outside = tmp_path / "outside-owned-fixture.md"
    outside.write_text("Private test fixture, outside the public catalog.")
    name = "alias"
    if alias_kind == "page":
        (root / "alias.md").symlink_to(outside)
    else:
        saved = root.with_name("saved-component")
        root.rename(saved)
        root.symlink_to(saved, target_is_directory=True)
        name = "SKILL"
    program = """import sys
sys.path.insert(0, sys.argv[1])
from scitex_sdk._bundled_skills import read_bundled_skill
try:
    read_bundled_skill('scitex-app', sys.argv[2])
except ValueError:
    print('rejected')
else:
    raise RuntimeError('resource alias was admitted')
"""
    return [sys.executable, "-I", "-c", program, str(tmp_path), name]


def test_bundled_reader_rejects_resource_aliases(resource_alias_command):
    # Arrange
    import subprocess

    command = resource_alias_command
    # Act
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=10, check=False
    )
    # Assert
    assert (result.returncode, result.stdout.strip()) == (0, "rejected"), result.stderr
