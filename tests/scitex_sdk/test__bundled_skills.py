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
