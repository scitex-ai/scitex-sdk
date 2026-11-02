"""Actual Django responses over package-only resources, without a server/DB."""

import json

import pytest
from django.test import RequestFactory

from scitex_sdk import list_bundled_skills
from scitex_sdk._web._views import bundled_skills


def test_get_serializes_actual_bundled_names_without_paths():
    # Arrange
    request = RequestFactory().get("/unmounted/skills")
    # Act
    response = bundled_skills(request)
    observed = json.loads(response.content)
    # Assert
    assert (response.status_code, observed, response["Content-Type"]) == (
        200,
        {"package": "scitex-sdk", "skills": list_bundled_skills()},
        "application/json",
    )


@pytest.mark.parametrize("method", ["post", "put", "delete", "patch", "head"])
def test_other_methods_are_refused_with_declared_json_error(method):
    # Arrange
    request = getattr(RequestFactory(), method)("/unmounted/skills")
    # Act
    response = bundled_skills(request)
    # Assert
    assert (
        response.status_code,
        response["Allow"],
        json.loads(response.content)["error"]["code"],
    ) == (405, "GET", "method_not_allowed")


def test_web_get_does_not_create_user_configuration_or_state(tmp_path):
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
        "import json;from types import SimpleNamespace;"
        'from django.conf import settings;settings.configure(DEFAULT_CHARSET="utf-8");'
        "from scitex_sdk._web._views import bundled_skills;"
        'response=bundled_skills(SimpleNamespace(method="GET"));'
        'print(json.dumps({"status":response.status_code,"body":json.loads(response.content)}))'
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
            "status": 200,
            "body": {"package": "scitex-sdk", "skills": list_bundled_skills()},
        },
        [],
    )


def test_physically_missing_bundle_returns_typed_error_without_paths(tmp_path):
    # Arrange
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    import scitex_sdk

    source = Path(scitex_sdk.__file__).parent
    for name in [
        "__init__.py",
        "_bundled_skills.py",
        "_web/__init__.py",
        "_web/_views.py",
    ]:
        target = tmp_path / "scitex_sdk" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    program = (
        "import sys,json;sys.path.insert(0,sys.argv[1]);"
        "from types import SimpleNamespace;"
        'from django.conf import settings;settings.configure(DEFAULT_CHARSET="utf-8");'
        "from scitex_sdk._web._views import bundled_skills;"
        'response=bundled_skills(SimpleNamespace(method="GET"));'
        'print(json.dumps({"status":response.status_code,"body":json.loads(response.content)}))'
    )
    # Act
    result = subprocess.run(
        [sys.executable, "-I", "-c", program, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    observed = json.loads(result.stdout)
    # Assert
    assert observed == {
        "status": 503,
        "body": {
            "error": {
                "code": "bundled_skills_unavailable",
                "message": "Bundled SDK skill resources are unavailable.",
            }
        },
    }
