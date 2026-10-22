#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_sdk.app.jail — the plugin-side filesystem jail.

Mirrors src/scitex_sdk/app/jail.py. Real Django requests
(RequestFactory, configured settings), real temp-dir jail roots, no
mocks: each test drives the production object and observes state.
"""

from __future__ import annotations

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["*"])
    django.setup()

from django.http import HttpResponse
from django.test import RequestFactory  # noqa: E402

from scitex_sdk.app.jail import (  # noqa: E402
    FIGRECIPE_JAIL_REFERENCE,
    FIGRECIPE_MOUNT_POLICY_REFERENCE,
    FORBIDDEN_MESSAGE,
    JailScopedView,
    first_escape,
    is_in_jail,
    jail_policy_of,
    normalize_jail_policy,
    parse_json_body,
    resolve_against,
    validate_mount_policy,
)
from scitex_sdk.app.plugins import LeafContractError  # noqa: E402

RF = RequestFactory()


# ---------------------------------------------------------------------------
# normalize_jail_policy: closed enum, loud typos
# ---------------------------------------------------------------------------

def test_true_shorthand_means_default_user_scope():
    # Arrange
    # Act
    jail = normalize_jail_policy(True, plugin="fig")
    # Assert
    assert (jail["scope"], jail["working_dir_param"], jail["path_params"]) == (
        "user",
        "working_dir",
        (),
    )


def test_typo_scope_fails_loud():
    # Arrange
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*scope"):
        normalize_jail_policy({"scope": "users"}, plugin="fig")


def test_string_path_params_refused():
    # Arrange
    # a bare string is iterable but never a key list
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*path_params"):
        normalize_jail_policy({"scope": "user", "path_params": "path"}, plugin="fig")


def test_empty_param_entry_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*path_params"):
        normalize_jail_policy(
            {"scope": "user", "path_params": ["path", " "]}, plugin="fig"
        )


def test_non_object_jail_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*jail"):
        normalize_jail_policy(["user"], plugin="fig")


# ---------------------------------------------------------------------------
# validate_mount_policy: the mount-time bar
# ---------------------------------------------------------------------------

def test_absent_policy_passes_open():
    # Arrange
    # Act
    jail = validate_mount_policy({}, plugin="fig")
    # Assert
    assert jail == {}


def test_file_touching_without_jail_fails_loud():
    # Arrange
    manifest = {"mount_policy": {"login_required": True, "touches_files": True}}
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*no.*jail"):
        validate_mount_policy(manifest, plugin="fig")


def test_jail_without_login_required_fails_loud():
    # Arrange
    # a jailed mount needs an authenticated user to jail TO
    manifest = {"mount_policy": {"touches_files": True, "jail": {"scope": "user"}}}
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*login_required"):
        validate_mount_policy(manifest, plugin="fig")


def test_non_bool_touches_files_fails_loud():
    # Arrange
    manifest = {"mount_policy": {"touches_files": "yes"}}
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*touches_files"):
        validate_mount_policy(manifest, plugin="fig")


def test_figrecipe_reference_block_validates_clean():
    # Arrange
    manifest = {"mount_policy": dict(FIGRECIPE_MOUNT_POLICY_REFERENCE)}
    # Act
    jail = validate_mount_policy(manifest, plugin="figrecipe")
    # Assert
    assert jail["path_params"] == ("path", "recipe", "recipe_path")


def test_figrecipe_reference_constant_matches_policy():
    # Arrange
    # Act
    jail = normalize_jail_policy(dict(FIGRECIPE_JAIL_REFERENCE), plugin="figrecipe")
    # Assert
    assert jail == validate_mount_policy(
        {"mount_policy": dict(FIGRECIPE_MOUNT_POLICY_REFERENCE)},
        plugin="figrecipe",
    )


def test_jail_policy_of_true_shorthand():
    # Arrange
    manifest = {"mount_policy": {"jail": True}}
    # Act
    raw = jail_policy_of(manifest)
    # Assert
    assert raw == {"scope": "user"}


# ---------------------------------------------------------------------------
# is_in_jail / resolve_against: component-wise containment
# ---------------------------------------------------------------------------

def test_sibling_prefix_is_not_containment(tmp_path):
    # Arrange
    # "proj" is a string prefix of "proj-secret"
    proj = tmp_path / "proj"
    proj.mkdir()
    sibling = tmp_path / "proj-secret" / "x"
    # Act
    inside = is_in_jail(sibling, proj)
    # Assert
    assert not inside


def test_dotdot_climb_rejected(tmp_path):
    # Arrange
    proj = tmp_path / "proj"
    proj.mkdir()
    # Act
    inside = is_in_jail(proj / ".." / "other", proj)
    # Assert
    assert not inside


def test_inside_passes(tmp_path):
    # Arrange
    target = tmp_path / "proj" / "a" / "b.yaml"
    # Act
    inside = is_in_jail(target, tmp_path / "proj")
    # Assert
    assert inside


def test_absolute_value_discards_base():
    # Arrange
    # pathlib's "/" drops the left operand: the attack shape
    # Act
    candidate = resolve_against("/srv/jail/alice/proj", "/etc/passwd")
    # Assert
    assert str(candidate) == "/etc/passwd"


def test_missing_root_fails_closed(tmp_path):
    # Arrange
    # Act
    inside = is_in_jail(tmp_path / "x", None)
    # Assert
    assert not inside


# ---------------------------------------------------------------------------
# first_escape: the shared predicate (query + body, joined + contained)
# ---------------------------------------------------------------------------

def test_absolute_query_value_escapes(tmp_path):
    # Arrange
    jail_root = tmp_path / "alice"
    jail_root.mkdir()
    working = jail_root / "proj"
    # Act
    hit = first_escape(
        {"path": "/etc/passwd"},
        {},
        path_params=("path",),
        working_dir=str(working),
        jail_root=jail_root,
    )
    # Assert
    assert hit == ("path", "/etc/passwd")


def test_dotdot_body_value_escapes(tmp_path):
    # Arrange
    jail_root = tmp_path / "alice"
    working = jail_root / "proj"
    # Act
    hit = first_escape(
        {},
        {"recipe": "../../bob/secret.yaml"},
        path_params=("recipe",),
        working_dir=str(working),
        jail_root=jail_root,
    )
    # Assert
    assert hit == ("recipe", "../../bob/secret.yaml")


def test_relative_inside_passes(tmp_path):
    # Arrange
    jail_root = tmp_path / "alice"
    working = jail_root / "proj"
    # Act
    hit = first_escape(
        {"path": "subdir/fig.yaml"},
        {"recipe": "other.yaml"},
        path_params=("path", "recipe"),
        working_dir=str(working),
        jail_root=jail_root,
    )
    # Assert
    assert hit is None


def test_undeclared_key_is_not_a_channel(tmp_path):
    # Arrange
    # keys outside path_params are invisible BY DESIGN; the
    # leaf must declare every key its handlers resolve
    jail_root = tmp_path / "alice"
    working = jail_root / "proj"
    # Act
    hit = first_escape(
        {"file_path": "/etc/passwd"},
        {},
        path_params=("path",),
        working_dir=str(working),
        jail_root=jail_root,
    )
    # Assert
    assert hit is None


def test_parse_json_body_non_object_is_empty():
    # Arrange
    request = RF.post("/x", data="[1,2]", content_type="application/json")
    # Act
    body = parse_json_body(request)
    # Assert
    assert body == {}


# ---------------------------------------------------------------------------
# JailScopedView: override + containment + extra_guard, end to end
# ---------------------------------------------------------------------------

def _harness(tmp_path, **kw):
    """Build (view, seen, jail_root, project_dir) with DI collaborators."""
    jail_root = tmp_path / "alice"
    project_dir = jail_root / "proj" / "p1"
    project_dir.mkdir(parents=True)
    seen = {}

    def downstream(request, *args, **kwargs):
        seen["working_dir"] = request.GET.get("working_dir")
        seen["args"] = args
        return HttpResponse("downstream-ok")

    def get_jail_root(request):
        return jail_root

    def resolve_working_dir(request):
        return project_dir

    def on_missing(request):
        return HttpResponse("no-project", status=404)

    view = JailScopedView(
        downstream,
        get_jail_root=get_jail_root,
        resolve_working_dir=resolve_working_dir,
        on_missing=on_missing,
        **kw,
    )
    return view, seen, jail_root, project_dir


def test_override_discards_caller_supplied_working_dir(tmp_path):
    # Arrange
    view, seen, _root, project_dir = _harness(
        tmp_path, jail={"scope": "user", "path_params": ["path"]}
    )
    request = RF.get("/api/switch", {"working_dir": "/home/victim/secret"})
    # Act
    response = view(request, "api/switch")
    # Assert
    assert (response.status_code, seen["working_dir"]) == (
        200,
        str(project_dir),
    )


def test_absolute_path_param_is_403(tmp_path):
    # Arrange
    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": ["path"]}
    )
    request = RF.get("/api/switch", {"path": "/etc/passwd"})
    # Act
    response = view(request, "api/switch")
    # Assert
    assert response.status_code == 403


def test_absolute_path_param_body_carries_forbidden_message(tmp_path):
    # Arrange
    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": ["path"]}
    )
    request = RF.get("/api/switch", {"path": "/etc/passwd"})
    # Act
    response = view(request, "api/switch")
    # Assert
    assert FORBIDDEN_MESSAGE in response.content.decode()


def test_body_dotdot_is_403(tmp_path):
    # Arrange
    import json

    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": ["recipe"]}
    )
    request = RF.post(
        "/api/open",
        data=json.dumps({"recipe": "../../../evil.yaml"}),
        content_type="application/json",
    )
    # Act
    response = view(request, "api/open")
    # Assert
    assert response.status_code == 403


def test_clean_request_reaches_downstream(tmp_path):
    # Arrange
    view, seen, _root, project_dir = _harness(
        tmp_path, jail={"scope": "user", "path_params": ["path"]}
    )
    request = RF.get("/api/switch", {"path": "figs/a.yaml"})
    # Act
    response = view(request, "api/switch")
    # Assert
    assert (response.status_code, seen["working_dir"]) == (
        200,
        str(project_dir),
    )


def test_no_project_fails_closed(tmp_path):
    # Arrange
    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": []}
    )
    view.resolve_working_dir = lambda request: None
    request = RF.get("/api/files")
    # Act
    response = view(request, "api/files")
    # Assert
    assert (response.status_code, seen) == (404, {})


def test_missing_jail_root_fails_closed(tmp_path):
    # Arrange
    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": []}
    )
    view.get_jail_root = lambda request: None
    request = RF.get("/api/files")
    # Act
    response = view(request, "api/files")
    # Assert
    assert (response.status_code, seen) == (403, {})


def test_extra_guard_sees_body_and_endpoint(tmp_path):
    # Arrange
    calls = []

    def extra_guard(request, body, *args, **kwargs):
        calls.append((args, body.get("template")))
        if body.get("template") == "../evil":
            from django.http import JsonResponse

            return JsonResponse({"error": FORBIDDEN_MESSAGE}, status=403)
        return None

    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": []}, extra_guard=extra_guard
    )
    import json

    request = RF.post(
        "/api/gallery/add",
        data=json.dumps({"template": "../evil"}),
        content_type="application/json",
    )
    # Act
    response = view(request, "api/gallery/add")
    # Assert
    assert response.status_code == 403


def test_extra_guard_receives_body_and_endpoint(tmp_path):
    # Arrange
    calls = []

    def extra_guard(request, body, *args, **kwargs):
        calls.append((args, body.get("template")))
        if body.get("template") == "../evil":
            from django.http import JsonResponse

            return JsonResponse({"error": FORBIDDEN_MESSAGE}, status=403)
        return None

    view, seen, _root, _proj = _harness(
        tmp_path, jail={"scope": "user", "path_params": []}, extra_guard=extra_guard
    )
    import json

    request = RF.post(
        "/api/gallery/add",
        data=json.dumps({"template": "../evil"}),
        content_type="application/json",
    )
    # Act
    response = view(request, "api/gallery/add")
    # Assert
    assert calls == [(("api/gallery/add",), "../evil")]


def test_malformed_jail_fails_at_construction(tmp_path):
    # Arrange
    _view, _seen, _root, _proj = _harness(tmp_path)
    downstream = lambda request, *a, **k: HttpResponse("x")  # noqa: E731
    # Act
    # Assert
    with pytest.raises(LeafContractError, match="fig.*scope"):
        JailScopedView(
            downstream,
            get_jail_root=lambda r: None,
            resolve_working_dir=lambda r: None,
            jail={"scope": "everywhere"},
            plugin="fig",
        )
