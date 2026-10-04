#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genuine database-free Django setup arbitration for companion installs.

Real ``django.setup()`` in a subprocess (isolated registries, no database):
the actual Fig primary + companion registers the ``scitex_app`` label, while
adding the canonical SDK ``scitex_sdk.app`` config (same label, different
module) fails loud with duplicate labels — never silently shadowed.

Runs only where the fleet source layout exists; skipped elsewhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SDK_SRC = Path(__file__).resolve().parents[3] / "src"
FIG_SRC = Path("/home/ywatanabe/proj/figrecipe/src")
LEGACY_SRC = Path("/home/ywatanabe/proj/scitex-app/src")

FLEET_LAYOUT = FIG_SRC.is_dir() and LEGACY_SRC.is_dir() and SDK_SRC.is_dir()

PROBE = """
import sys, json
sys.path.insert(0, "@LEGACY@")
sys.path.insert(0, "@FIG@")
sys.path.insert(0, "@SDK@")
import django
from django.conf import settings
settings.configure(
    DEBUG=False, DATABASES={},
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"] + @APPS@,
    USE_TZ=True,
)
try:
    django.setup()
except Exception as exc:  # noqa: BLE001 — the failure shape is the assertion
    print(json.dumps({"setup": "RAISED", "error": f"{type(exc).__name__}: {exc}"}))
else:
    from django.apps import apps as reg
    try:
        model = reg.get_model("scitex_app", "ChatSession")
        chat = f"{model.__module__}.{model.__name__}"
    except Exception as exc:  # noqa: BLE001
        chat = f"UNREGISTERED {type(exc).__name__}"
    print(json.dumps({
        "setup": "OK",
        "labels": sorted(c.label for c in reg.get_app_configs()),
        "chat_session": chat,
    }))
"""


def _run_setup(extra_apps):
    # Arrange
    code = (
        PROBE.replace("@LEGACY@", str(LEGACY_SRC))
        .replace("@FIG@", str(FIG_SRC))
        .replace("@SDK@", str(SDK_SRC))
        .replace("@APPS@", repr(extra_apps))
    )
    # Act
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    # Assert
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not FLEET_LAYOUT, reason="needs fleet source layout")
def test_fig_primary_plus_companion_registers_label():
    # Arrange
    apps = [
        "figrecipe._django.apps.FigRecipeEditorConfig",
        "figrecipe._django.apps.ScitexAppChatConfig",
    ]
    # Act
    result = _run_setup(apps)
    # Assert
    assert result["setup"] == "OK" and "scitex_app" in result["labels"]


@pytest.mark.skipif(not FLEET_LAYOUT, reason="needs fleet source layout")
def test_canonical_sdk_config_plus_companion_fails_loud():
    # Arrange — same label, different modules: must never silently shadow.
    apps = [
        "scitex_sdk.app.apps.ScitexAppConfig",
        "figrecipe._django.apps.ScitexAppChatConfig",
    ]
    # Act
    result = _run_setup(apps)
    # Assert
    assert result["setup"] == "RAISED" and "duplicates: scitex_app" in result["error"]
