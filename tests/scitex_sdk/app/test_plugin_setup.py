#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genuine database-free Django setup arbitration for companion installs.

Real ``django.setup()`` in a subprocess (isolated registries, no database):
the leaf tuple flows through :func:`partition_companions` and
:func:`installed_app_paths` — the owned helper path, not hand-picked lists —
and the resulting settings are booted for real.

The leaf mirrors the Fig shape (bare primary module plus an explicit
companion in the entry tuple); the companion under test is the actual
canonical SDK chat config, so model/migration identity is proved, not
assumed. ``makemigrations --check`` proves the shipped migration state
matches the models with no database involved. Everything besides the SDK
itself is scaffolded in ``tmp_path``: hermetic, bounded, CI-safe.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SDK_SRC = Path(__file__).resolve().parents[3] / "src"

PROBE = """
import sys, json
sys.path.insert(0, "@SYN@")
sys.path.insert(0, "@SDK@")
import django
from django.conf import settings
from scitex_sdk.app.plugins import PluginApp, installed_app_paths, partition_companions
entries = ("synleaf", "scitex_sdk.app._chat.apps.ScitexAppChatConfig")
plugins = [PluginApp("syn", "synleaf.apps.SynPrimaryConfig")]
companions = partition_companions(entries, plugins)
settings.configure(
    DEBUG=False, DATABASES={},
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"]
    + installed_app_paths(@EXISTING@, plugins, companions),
    USE_TZ=True,
)
report = {"installed": settings.INSTALLED_APPS}
try:
    django.setup()
except Exception as exc:  # noqa: BLE001 — the failure shape is the assertion
    report.update({"setup": "RAISED", "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(report))
else:
    from django.apps import apps as reg
    from django.core.management import call_command
    try:
        model = reg.get_model("scitex_app", "ChatSession")
        chat = f"{model.__module__}.{model.__name__}"
    except Exception as exc:  # noqa: BLE001
        chat = f"UNREGISTERED {type(exc).__name__}"
    try:
        call_command("makemigrations", "scitex_app", check=True, dry_run=True, verbosity=0)
        migrations = "IN-SYNC"
    except SystemExit:
        migrations = "CHANGES-DETECTED"
    report.update({
        "setup": "OK",
        "installed": settings.INSTALLED_APPS,
        "labels": sorted(c.label for c in reg.get_app_configs()),
        "chat_session": chat,
        "migrations": migrations,
    })
    print(json.dumps(report))
"""


def _scaffold(tmp_path: Path) -> None:
    (tmp_path / "synleaf").mkdir(exist_ok=True)
    (tmp_path / "synleaf" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "synleaf" / "apps.py").write_text(
        "from django.apps import AppConfig\n"
        "\n"
        "class SynPrimaryConfig(AppConfig):\n"
        "    default = True\n"
        "    name = 'synleaf'\n"
        "    label = 'syn_primary'\n",
        encoding="utf-8",
    )
    (tmp_path / "synother").mkdir(exist_ok=True)
    (tmp_path / "synother" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "synother" / "apps.py").write_text(
        "from django.apps import AppConfig\n"
        "\n"
        "class SynClashConfig(AppConfig):\n"
        "    name = 'synother'\n"
        "    label = 'scitex_app'\n",
        encoding="utf-8",
    )


def _run_setup(tmp_path: Path, existing: list) -> dict:
    # Arrange
    code = PROBE.replace("@SYN@", str(tmp_path)).replace("@SDK@", str(SDK_SRC)).replace(
        "@EXISTING@", repr(existing)
    )
    # Act
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
    )
    # Assert
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_helper_path_boots_without_duplicate_primary(tmp_path):
    # Arrange
    _scaffold(tmp_path)
    # Act
    result = _run_setup(tmp_path, [])
    # Assert — bare primary dropped by partition, exact entries installed once.
    assert result["installed"] == [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "synleaf.apps.SynPrimaryConfig",
        "scitex_sdk.app._chat.apps.ScitexAppChatConfig",
    ]


def test_chat_models_register_from_sdk_canonical_module(tmp_path):
    # Arrange
    _scaffold(tmp_path)
    # Act
    result = _run_setup(tmp_path, [])
    # Assert
    assert result["chat_session"] == "scitex_sdk.app._chat._models.ChatSession"


def test_shipped_migrations_match_models_without_database(tmp_path):
    # Arrange
    _scaffold(tmp_path)
    # Act
    result = _run_setup(tmp_path, [])
    # Assert
    assert result["migrations"] == "IN-SYNC"


def test_second_scitex_app_label_fails_loud(tmp_path):
    # Arrange — same label, different module: shadowing is refused, not merged.
    _scaffold(tmp_path)
    # Act
    result = _run_setup(tmp_path, ["synother.apps.SynClashConfig"])
    # Assert
    assert result["setup"] == "RAISED" and "duplicates: scitex_app" in result["error"]

CORE_PROBE = """
import sys, json
sys.path.insert(0, "@SDK@")
import django
from django.conf import settings
from scitex_sdk.app.plugins import installed_app_paths
settings.configure(
    DEBUG=False, DATABASES={},
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"]
    + installed_app_paths(
        ["scitex_sdk.app.apps.ScitexAppConfig"],
        [],
        ["scitex_sdk.app._chat.apps.ScitexAppChatConfig"],
    ),
    USE_TZ=True,
)
report = {"installed": settings.INSTALLED_APPS}
try:
    django.setup()
except Exception as exc:  # noqa: BLE001 — the failure shape is the assertion
    report.update({"setup": "RAISED", "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(report))
else:
    from django.apps import apps as reg
    from django.core.management import call_command
    from django.db.migrations.loader import MigrationLoader
    message = reg.get_model("scitex_app", "ChatMessage")
    loader = MigrationLoader(None, load=False)
    loader.load_disk()
    disk = sorted(
        name for (app, name) in loader.disk_migrations if app == "scitex_app"
    )
    try:
        call_command("makemigrations", "scitex_app", check=True, dry_run=True, verbosity=0)
        migrations = "IN-SYNC"
    except SystemExit:
        migrations = "CHANGES-DETECTED"
    report.update({
        "setup": "OK",
        "labels": sorted(c.label for c in reg.get_app_configs()),
        "chat_message": f"{message.__module__}.{message.__name__}",
        "disk_migration": disk,
        "migrations": migrations,
    })
    print(json.dumps(report))
"""


def _run_core_setup() -> dict:
    # Arrange
    code = CORE_PROBE.replace("@SDK@", str(SDK_SRC))
    # Act
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
    )
    # Assert
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_core_plus_chat_canonical_setup():
    # Arrange — relabelled canonical coexists with the chat owner.
    # Act
    result = _run_core_setup()
    # Assert
    assert result["setup"] == "OK" and sorted(result["labels"]) == [
        "auth",
        "contenttypes",
        "scitex_app",
        "scitex_sdk_app",
    ]


def test_chat_message_resolves_from_sdk_canonical_models():
    # Arrange
    # Act
    result = _run_core_setup()
    # Assert
    assert result["chat_message"] == "scitex_sdk.app._chat._models.ChatMessage"


def test_migration_loader_sees_shipped_initial():
    # Arrange
    # Act
    result = _run_core_setup()
    # Assert
    assert result["disk_migration"] == ["0001_initial"] and result["migrations"] == "IN-SYNC"
