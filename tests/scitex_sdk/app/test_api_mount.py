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
        admission = admit(ref, review_ref="review-1", enabled=[])
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
            resolve_handler(_ref(), admit(_ref(), review_ref="review-1", enabled=[]), "ping")
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
                admit(_ref(), review_ref="review-1", enabled=["ping"]),
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
        handler = resolve_handler(_ref(), admit(_ref(), review_ref="review-1", enabled=["ping"]), "ping")
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
            resolve_handler(_ref(), admit(_ref(), review_ref="review-1", enabled=["ping"]), "other")
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


def _write_dual_leaf(tmp_path):
    # Arrange
    pkg = tmp_path / "dualpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "views.py").write_text(
        "from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit\n"
        "PUBLIC = AuthScope(public=True, project_scope='none')\n"
        "class Handlers:\n"
        "    @staticmethod\n"
        "    def get_thing(request, editor):\n"
        "        return {'side': 'get'}\n"
        "    @staticmethod\n"
        "    def post_thing(request, editor):\n"
        "        return {'side': 'post'}\n"
        "NOT_A_HANDLER = 42\n"
        "PLUGIN = ApiPlugin(id='dual', title='Dual', api_version='1.0.0', routes=[\n"
        "    ApiRoute(path='thing', methods=['GET'], rate=RateLimit(rate_class='free', compute_cost='low'), auth=PUBLIC, handler='dualpkg.views:Handlers.get_thing'),\n"
        "    ApiRoute(path='thing', methods=['POST'], rate=RateLimit(rate_class='free', compute_cost='low'), auth=PUBLIC, handler='dualpkg.views:Handlers.post_thing', read_only=True),\n"
        "    ApiRoute(path='data', methods=['GET'], rate=RateLimit(rate_class='free', compute_cost='low'), auth=PUBLIC, handler='dualpkg.views:NOT_A_HANDLER'),\n"
        "])\n",
        encoding="utf-8",
    )
    # Act
    import sys
    sys.path.insert(0, str(tmp_path))
    # Assert
    assert True


def _dual_ref():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPluginRef
    # Act
    # Assert
    return ApiPluginRef(name="dual", target="dualpkg.views:PLUGIN", distribution="dual-dist")


def test_method_disjoint_routes_resolve_each_side(tmp_path):
    # Arrange
    _write_dual_leaf(tmp_path)
    try:
        # Act
        admission = admit(_dual_ref(), review_ref="review-1", enabled=["thing", "data"])
        get_handler = resolve_handler(_dual_ref(), admission, "thing", method="GET")
        post_handler = resolve_handler(_dual_ref(), admission, "thing", method="POST")
    finally:
        import sys
        sys.path.remove(str(tmp_path))
        sys.modules.pop("dualpkg.views", None)
        sys.modules.pop("dualpkg", None)
    # Assert
    assert get_handler(None, None) == {"side": "get"} and post_handler(None, None) == {"side": "post"}


def test_undeclared_method_refused(tmp_path):
    # Arrange
    _write_dual_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            resolve_handler(_dual_ref(), admit(_dual_ref(), review_ref="review-1", enabled=["thing"]), "thing", method="DELETE")
    finally:
        import sys
        sys.path.remove(str(tmp_path))
        sys.modules.pop("dualpkg.views", None)
        sys.modules.pop("dualpkg", None)


def test_non_callable_handler_refused(tmp_path):
    # Arrange
    _write_dual_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            resolve_handler(_dual_ref(), admit(_dual_ref(), review_ref="review-1", enabled=["data"]), "data")
    finally:
        import sys
        sys.path.remove(str(tmp_path))
        sys.modules.pop("dualpkg.views", None)
        sys.modules.pop("dualpkg", None)


def test_session_and_read_only_declare_natively():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit
    # Act
    route = ApiRoute(path="query", methods=["POST"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(session=True), read_only=True, handler="m:h")
    # Assert
    assert route.auth.session is True and route.read_only is True


def test_read_only_with_put_refused():
    # Arrange
    import pytest as _pytest
    from scitex_sdk.app.api_plugin import ApiPluginContractError, ApiRoute, AuthScope, RateLimit
    # Act
    # Assert
    with _pytest.raises(ApiPluginContractError):
        ApiRoute(path="query", methods=["PUT"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(public=True, project_scope="none"), read_only=True, handler="m:h")


def test_session_with_scopes_refused():
    # Arrange
    import pytest as _pytest
    from scitex_sdk.app.api_plugin import ApiPluginContractError, AuthScope
    # Act
    # Assert
    with _pytest.raises(ApiPluginContractError):
        AuthScope(session=True, scopes=["read"])


def test_require_admitted_passes_match_without_import(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        api_mount.require_admitted(_ref(), admit(_ref(), review_ref="review-1", enabled=["ping"]))
    finally:
        _unpath(tmp_path)
    # Assert
    assert _marker_absent(tmp_path)


def test_require_admitted_refuses_drift_without_import(tmp_path):
    # Arrange
    _write_leaf(tmp_path)
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            api_mount.require_admitted(
                ApiPluginRef(name="leafprobe", target="leafprobe_pkg.views:OTHER", distribution="leafprobe-dist"),
                admit(_ref(), review_ref="review-1", enabled=["ping"]),
            )
    finally:
        _unpath(tmp_path)
    # Assert
    assert _marker_absent(tmp_path)


def test_oauth_scoped_plugin_round_trip():
    # Arrange
    from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, OAuthProvider, RateLimit
    plugin = ApiPlugin(id="scoped", title="Scoped", api_version="1.0.0", routes=[
        ApiRoute(path="data", methods=["GET"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(scopes=["read"]), handler="m:h"),
    ], oauth=OAuthProvider(authorization_url="https://auth.example.com/authorize", token_url="https://auth.example.com/token", scopes={"read": "Read access"}))
    # Act
    restored = _build_for_test(plugin)
    # Assert
    assert restored == plugin


def _build_for_test(plugin):
    # Arrange
    import json
    from scitex_sdk.app import api_mount
    # Act
    # Assert
    return api_mount._build(api_mount.ApiPlugin, json.loads(api_mount.dump_inert_descriptor(plugin)))


def test_invalid_utf8_descriptor_denied(tmp_path):
    # Arrange
    dist_info = tmp_path / "baddist-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: baddist\nVersion: 1.0\n", encoding="utf-8")
    (dist_info / "scitex_api.json").write_bytes(b"\xff\xfe invalid \xff")
    sys.path.insert(0, str(tmp_path))
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            read_inert_descriptor("baddist")
    finally:
        sys.path.remove(str(tmp_path))


def test_read_only_falsy_non_bool_refused():
    # Arrange
    import pytest as _pytest
    from scitex_sdk.app.api_plugin import ApiPluginContractError, ApiRoute, AuthScope, RateLimit
    # Act
    refused = 0
    for bad in (0, None, ""):
        try:
            ApiRoute(path="query", methods=["GET"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(public=True, project_scope="none"), read_only=bad, handler="m:h")
        except ApiPluginContractError:
            refused += 1
    # Assert
    assert refused == 3


def test_lookup_failure_denied_not_absent(tmp_path):
    # Arrange: a real installed distribution carrying a malformed inert
    # descriptor, so the reader denies instead of reporting absent. No mocks:
    # the failure comes from real files, not a patched finder. (An unreadable
    # METADATA would read as absent; the denied path needs corrupt content.)
    from scitex_sdk.app.api_mount import INERT_DESCRIPTOR_FILENAME

    dist_dir = tmp_path / "brokendist-0.0.0.dist-info"
    dist_dir.mkdir()
    (dist_dir / "METADATA").write_text(
        "Name: brokendist\nVersion: 0.0.0\n", encoding="utf-8"
    )
    (dist_dir / INERT_DESCRIPTOR_FILENAME).write_text("{not json", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        # Act
        # Assert
        with pytest.raises(AdmissionDenied):
            read_inert_descriptor("brokendist")
    finally:
        sys.path.remove(str(tmp_path))


def test_admitted_routes_intersects_declaration_with_admission():
    # Arrange
    from scitex_sdk.app.api_mount import admitted_routes
    from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit
    plugin = ApiPlugin(id="p", title="P", api_version="1.0.0", routes=[
        ApiRoute(path="a", methods=["GET"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(public=True, project_scope="none"), handler="m:h"),
        ApiRoute(path="b", methods=["POST"], rate=RateLimit(rate_class="free", compute_cost="low"), auth=AuthScope(public=True, project_scope="none"), handler="m:h", read_only=True),
    ])
    admission = admit(_ref(), review_ref="review-1", enabled=["a"])
    # Act
    pairs = admitted_routes(plugin, admission)
    # Assert
    assert pairs == [("a", ("GET",))]


def test_admitted_routes_refuses_non_plugin():
    # Arrange
    import pytest as _pytest
    from scitex_sdk.app.api_mount import admitted_routes
    # Act
    # Assert
    with _pytest.raises(AdmissionDenied):
        admitted_routes(object(), admit(_ref(), review_ref="review-1", enabled=[]))
