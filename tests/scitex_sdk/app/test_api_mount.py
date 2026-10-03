#!/usr/bin/env python3
"""Opt-in leaf API admission: deny before import, enable explicitly.

An unapproved module's import side effects stay untouched through
discovery, listing, and denied activation; only an admitted reference
resolves, and only for enabled paths. Inert descriptors display without
executing leaf code.
"""

from __future__ import annotations

import json
import sys

import pytest

from scitex_sdk.app import api_mount
from scitex_sdk.app.api_mount import (
    AdmissionDenied,
    admit,
    dump_inert_descriptor,
    read_inert_descriptor,
    resolve_handler,
)
from scitex_sdk.app.api_plugin import ApiPlugin, ApiPluginRef, ApiRoute, AuthScope, RateLimit


_PUBLIC = AuthScope(public=True, project_scope="none")


LEAF_PKG = "leafprobe_pkg"
LEAF_VIEWS = LEAF_PKG + ".views"


def _write_leaf(tmp_path):
    # Arrange
    pkg = tmp_path / LEAF_PKG
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "views.py").write_text(
        "from pathlib import Path\n"
        "Path(__file__).parent.joinpath('IMPORTED.txt').write_text('x')\n"
        "from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit\n"
        "def ping_handler(request, editor):\n"
        "    return {'ok': True}\n"
        "PLUGIN = ApiPlugin(id='leafprobe', title='Leaf', api_version='1.0.0', routes=[\n"
        "    ApiRoute(path='ping', methods=['GET'], rate=RateLimit(rate_class='free', compute_cost='low'), auth=AuthScope(public=True, project_scope='none'), handler='leafprobe_pkg.views:ping_handler'),\n"
        "])\n",
        encoding="utf-8",
    )
    # Act
    sys.path.insert(0, str(tmp_path))
    # Assert
    assert True


def _marker_absent(tmp_path):
    # Arrange
    # Act
    missing = not (tmp_path / LEAF_PKG / "IMPORTED.txt").exists()
    # Assert
    return missing


def _unpath(tmp_path):
    # Arrange
    # Act
    sys.path.remove(str(tmp_path))
    for name in [LEAF_PKG, LEAF_VIEWS]:
        sys.modules.pop(name, None)
    # Assert
    assert True


def _ref():
    # Arrange
    return ApiPluginRef(name="leafprobe", target=LEAF_PKG + ".views:PLUGIN", distribution="leafprobe-dist")


def test_discovery_never_imports_leaf(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        ref = _ref()
        admission = admit(ref, source="review-1", enabled=[])
    finally:
        _unpath(tmp_path)
    # Assert
    assert admission.enabled == () and _marker_absent(tmp_path)


def test_denied_path_imports_nothing(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            resolve_handler(_ref(), admit(_ref(), source="review-1", enabled=[]), "ping")
    finally:
        _unpath(tmp_path)
    # Assert
    assert _marker_absent(tmp_path)


def test_changed_target_refused_before_import(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            resolve_handler(
                ApiPluginRef(name="leafprobe", target=LEAF_PKG + ".views:OTHER", distribution="leafprobe-dist"),
                admit(_ref(), source="review-1", enabled=["ping"]),
                "ping",
            )
    finally:
        _unpath(tmp_path)
    # Assert
    assert _marker_absent(tmp_path)


def test_admitted_reference_resolves_only_enabled_path(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        handler = resolve_handler(_ref(), admit(_ref(), source="review-1", enabled=["ping"]), "ping")
        # Assert
        assert handler({"m": "GET"}, None) == {"ok": True}
    finally:
        _unpath(tmp_path)


def test_undeclared_path_denied_after_admission(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            resolve_handler(_ref(), admit(_ref(), source="review-1", enabled=["ping"]), "other")
    finally:
        _unpath(tmp_path)


def test_inert_round_trip_without_import(tmp_path):
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, RateLimit
    plugin = ApiPlugin(id="leafprobe", title="Leaf", api_version="1.0.0", routes=[
        ApiRoute(path="ping", methods=["GET"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=_PUBLIC, handler="leafprobe_pkg.views:ping_handler"),
    ])
    # Act
    text = dump_inert_descriptor(plugin)
    data = json.loads(text)
    # Assert
    assert data["id"] == "leafprobe" and data["routes"][0]["path"] == "ping" and LEAF_PKG not in sys.modules


def test_inert_malformed_refused(tmp_path):
    # Arrange
    dist_info = tmp_path / "leafprobe_dist-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: leafprobe-dist\nVersion: 1.0\n", encoding="utf-8")
    (dist_info / "scitex_api.json").write_text('{"id": 42}', encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            read_inert_descriptor("leafprobe-dist")
    finally:
        sys.path.remove(str(tmp_path))


def test_inert_absent_yields_none():
    # Arrange
    # Act
    found = read_inert_descriptor("no-such-distribution-xyz")
    # Assert
    assert found is None


def test_inert_round_trip_restores_equal_plugin(tmp_path):
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, RateLimit
    from scitex_sdk.app.api_mount import read_inert_descriptor as read_back

    plugin = ApiPlugin(id="leafprobe", title="Leaf", api_version="1.0.0", routes=[
        ApiRoute(path="ping", methods=["GET"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=_PUBLIC, handler="leafprobe_pkg.views:ping_handler"),
    ])
    dist_info = tmp_path / "leafprobe_dist-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: leafprobe-dist\nVersion: 1.0\n", encoding="utf-8")
    (dist_info / "scitex_api.json").write_text(dump_inert_descriptor(plugin), encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        # Act
        restored = read_back("leafprobe-dist")
    finally:
        sys.path.remove(str(tmp_path))
    # Assert
    assert restored == plugin


# EOF
