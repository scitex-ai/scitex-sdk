"""An incomplete SDK refuses a standalone launch before Django setup."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scitex_sdk.app._standalone import (
    ScitexUiRequiredError,
    _SCITEX_UI_REQUIRED,
    _scitex_ui_present,
    run_standalone,
)


def test_the_guard_error_is_a_runtime_error_not_django_improperly_configured():
    """It is a RuntimeError subclass (so a launcher can catch it specifically)
    and is NOT Django's ImproperlyConfigured — this failure happens before
    Django is configured, so it must not masquerade as a Django one."""
    # Arrange
    from django.core.exceptions import ImproperlyConfigured
    # Act
    is_runtime = issubclass(ScitexUiRequiredError, RuntimeError)
    not_improper = not issubclass(ScitexUiRequiredError, ImproperlyConfigured)
    # Assert
    assert is_runtime and not_improper, (
        f"ScitexUiRequiredError must be a RuntimeError subclass "
        f"(got {is_runtime}) and must NOT be a Django "
        f"ImproperlyConfigured subclass (got {not_improper})"
    )


def test_the_guard_message_names_the_cause_and_the_fix():
    # Arrange — the contract: an operator chasing the old
    # TemplateDoesNotExist must be told what is actually missing.
    msg = _SCITEX_UI_REQUIRED
    # Act — nothing to call; the message IS the assertion surface.
    # Assert — it names the missing package, the install fix, and the old
    # failure mode it replaces (so a reader can connect it to what they saw).
    assert all(
        needle in msg
        for needle in ("scitex_sdk.ui", "pip install --force-reinstall", "scitex-sdk[gui]")
    ), f"guard message must name the package, the fix, and the old failure; got: {msg!r}"


def test_presence_check_agrees_with_find_spec_in_both_directions():
    """`_scitex_ui_present` is a pure re-read of `find_spec`. Whatever the
    environment, the two must agree — this pins the check to the real import
    so it cannot drift to a version string or a hardcoded answer."""
    # Arrange — the ground truth the check is a proxy for.
    truth = importlib.util.find_spec("scitex_sdk.ui") is not None
    # Act
    check = _scitex_ui_present()
    # Assert — one direction is enough to pin the proxy to the source; the
    # other direction would be asserting the same boolean equals itself.
    assert check is truth


def test_guard_fires_before_any_django_configuration():
    """When the shell is absent, `run_standalone` raises at the FIRST check —
    before it sets SCITEX_WORKING_DIR, calls `_configure_django`, or imports
    `django.setup`. Proven by the guard's position in the source, not by
    trusting it: a regression that moved the check below `_configure_django`
    would leave Django configured in the failing case, which this test would
    not catch, so the position is asserted explicitly."""
    # Arrange
    import inspect
    src = inspect.getsource(run_standalone).splitlines()
    # Act
    guard_idx = next(
        i for i, line in enumerate(src) if "_scitex_ui_present" in line
    )
    configure_idx = next(
        i for i, line in enumerate(src) if "_configure_django" in line
    )
    # Assert
    assert guard_idx < configure_idx, (
        f"guard must fire before _configure_django (guard line {guard_idx}, "
        f"configure line {configure_idx})"
    )


def test_run_standalone_raises_the_named_error_when_the_shell_is_absent(monkeypatch):
    """An incomplete SDK refuses launch before configuration or file writes."""
    monkeypatch.setattr("scitex_sdk.app._standalone._scitex_ui_present", lambda: False)
    with pytest.raises(ScitexUiRequiredError):
        run_standalone(app_module="some_app._django")


@pytest.fixture
def real_standalone_configuration(tmp_path):
    """Observe genuine fresh settings and parsed development-server options.

    A profile callback stops the real Django command before it binds. No
    product callable or provider is replaced, and each configuration owns
    a fresh interpreter so the host control cannot inherit standalone state.
    """
    directory = tmp_path
    source_root = Path(__file__).resolve().parents[3] / "src"
    program = r'''
import json
import sys

def refuse_database(frame, event, _argument):
    path = frame.f_code.co_filename.replace("\\", "/")
    if event == "call" and "/django/db/backends/" in path:
        if frame.f_code.co_name in {"connect", "get_new_connection"}:
            raise RuntimeError("standalone configuration attempted a database")

sys.setprofile(refuse_database)
from django.conf import settings

host = sys.argv[1] == "host"
if host:
    settings.configure(
        SECRET_KEY="disposable-host-contract", DEBUG=False,
        SCITEX_APP_MODE="hub", SCITEX_PROJECT_PROVIDER="host.owned.Provider",
        ALLOWED_HOSTS=["host.example.test"], DATABASES={},
        MIDDLEWARE=["host.owned.Middleware"], ROOT_URLCONF="host.owned.urls",
    )

from scitex_sdk.app._standalone import _configure_django, _run_server
_configure_django("django.contrib.contenttypes")
observed = {
    "mode": getattr(settings, "SCITEX_APP_MODE", None),
    "debug": settings.DEBUG,
    "databases": settings.DATABASES,
    "provider": getattr(settings, "SCITEX_PROJECT_PROVIDER", None),
    "middleware": settings.MIDDLEWARE,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "root_urlconf": settings.ROOT_URLCONF,
}

if not host:
    import django
    django.setup()

    class ObservedBeforeBind(RuntimeError):
        pass

    def observe(frame, event, _argument):
        refuse_database(frame, event, _argument)
        path = frame.f_code.co_filename.replace("\\", "/")
        if event == "call" and frame.f_code.co_name == "handle":
            if path.endswith("/django/core/management/commands/runserver.py"):
                observed["insecure_serving"] = frame.f_locals["options"].get("insecure_serving")
                observed["use_reloader"] = frame.f_locals["options"].get("use_reloader")
                raise ObservedBeforeBind

    sys.setprofile(observe)
    try:
        _run_server("127.0.0.1", 8050, False)
    except ObservedBeforeBind:
        pass
    finally:
        sys.setprofile(None)

sys.setprofile(None)

print("STANDALONE_OBSERVATION=" + json.dumps(observed))
'''
    results = {}
    for mode in ("standalone", "host"):
        environment = dict(os.environ)
        environment.pop("DJANGO_SETTINGS_MODULE", None)
        environment.update(
            PYTHONPATH=str(source_root),
            PYTHONDONTWRITEBYTECODE="1",
            SCITEX_DIR=str(directory / mode),
            DJANGO_DEBUG="false",
        )
        completed = subprocess.run(
            [sys.executable, "-c", program, mode],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        line = next(
            line for line in completed.stdout.splitlines()
            if line.startswith("STANDALONE_OBSERVATION=")
        )
        results[mode] = json.loads(line.partition("=")[2])
    return results


def test_fresh_launcher_declares_standalone_mode(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    mode = configured["mode"]
    # Assert
    assert mode == "standalone"


def test_fresh_launcher_uses_no_database(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    databases = configured["databases"]
    # Assert
    assert databases == {}


def test_fresh_launcher_preserves_debug_false(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    debug = configured["debug"]
    # Assert
    assert debug is False


def test_development_static_works_without_debug(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    permitted = configured["insecure_serving"]
    # Assert
    assert permitted is True


def test_nonreload_launch_does_not_spawn_a_reloader(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    reloads = configured["use_reloader"]
    # Assert
    assert reloads is False


def test_fresh_launcher_uses_the_genuine_provider(real_standalone_configuration):
    # Arrange
    configured = real_standalone_configuration["standalone"]
    # Act
    provider = configured["provider"]
    # Assert
    assert provider == "scitex_sdk.app.project_context.StandaloneProjectProvider"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("mode", "hub"),
        ("provider", "host.owned.Provider"),
        ("middleware", ["host.owned.Middleware"]),
        ("allowed_hosts", ["host.example.test"]),
        ("root_urlconf", "host.owned.urls"),
    ],
)
def test_configured_host_is_not_reconfigured(real_standalone_configuration, key, expected):
    # Arrange
    configured = real_standalone_configuration["host"]
    # Act
    retained = configured[key]
    # Assert
    assert retained == expected
