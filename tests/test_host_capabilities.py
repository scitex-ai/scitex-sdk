"""Host authority and local capabilities against only synthetic workspaces."""
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from django.test import RequestFactory, override_settings
from scitex_sdk.host import (AccessError, CapabilityUnavailable, ProjectAccess,
                             StoreAccess, authenticated_user, project_access, store_access)
from scitex_sdk.ui.project_scope import ProjectEntry
from scitex_sdk.local import LocalProjectStorage, LocalProjectStore


class Projects:
    def __init__(self):
        self.selected = "owned"
        self.selections = []

    def list_projects(self, request):
        return [ProjectEntry("owned", "Owned")]

    def last_visited(self, request):
        return self.selected

    def remember(self, request, project_id):
        self.selections.append(project_id)
        self.selected = project_id


class Storage:
    def __init__(self, root, writable=True):
        self.root, self.writable, self.calls = root, writable, []

    def project_path(self, project_id, request):
        self.calls.append(project_id)
        return self.root if project_id == "owned" else None

    def can_write(self, project_id, request):
        return self.writable


@pytest.fixture
def hosted(tmp_path, monkeypatch):
    projects, storage = Projects(), Storage(tmp_path)
    monkeypatch.setattr(__import__(__name__, fromlist=["_"]), "_projects", projects, raising=False)
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_PROVIDER=__name__ + "._projects",
                           SCITEX_PROJECT_STORAGE=storage, SCITEX_PROJECT_STORE=None):
        yield projects, storage


def request(authenticated=True, project="owned"):
    req = RequestFactory().get("/", {"project": project})
    req.user = SimpleNamespace(is_authenticated=authenticated)
    return req


def test_anonymous_host_access_refuses_before_project_or_storage(hosted):
    projects, storage = hosted
    with pytest.raises(AccessError) as failure:
        project_access(request(False))
    assert failure.value.status == 401
    assert projects.selections == [] and storage.calls == []


def test_denied_explicit_project_cannot_fall_back_or_reach_storage(hosted):
    projects, storage = hosted
    with pytest.raises(AccessError) as failure:
        project_access(request(project="foreign"))
    assert failure.value.status == 404
    assert projects.selected == "owned" and projects.selections == [] and storage.calls == []


@pytest.mark.parametrize("setting", ["SCITEX_PROJECT_PROVIDER", "SCITEX_PROJECT_STORAGE"])
def test_missing_host_capability_has_no_local_fallback(hosted, setting):
    with override_settings(**{setting: None}):
        with pytest.raises(CapabilityUnavailable):
            project_access(request())


@pytest.mark.parametrize("writable", [False, None, 0, 1, "true", "false"])
def test_write_authority_requires_literal_true(hosted, writable):
    _, storage = hosted
    storage.writable = writable
    with pytest.raises(AccessError) as failure:
        project_access(request(), write=True)
    assert failure.value.status == 403


def test_authorized_project_is_the_host_workspace(hosted):
    _, storage = hosted
    result = project_access(request(), write=True)
    assert result == ProjectAccess("owned", "Owned", storage.root.resolve(), True)


def test_project_path_refuses_traversal_and_foreign_symlink(tmp_path):
    root, foreign = tmp_path / "owned", tmp_path / "foreign"
    root.mkdir(); foreign.mkdir()
    (root / "foreign-link").symlink_to(foreign, target_is_directory=True)
    capability = ProjectAccess("owned", "Owned", root)
    assert capability.path("valid.txt") == root / "valid.txt"
    for relative in ["../foreign/data.txt", "foreign-link/data.txt"]:
        with pytest.raises(AccessError):
            capability.path(relative)


def test_authenticator_is_only_the_explicit_host_provider():
    anonymous = request(False)
    expected = object()
    with override_settings(SCITEX_API_AUTHENTICATOR=None):
        assert authenticated_user(anonymous) is None
    with override_settings(SCITEX_API_AUTHENTICATOR=lambda req: expected):
        assert authenticated_user(anonymous) is expected
    session = request()
    assert authenticated_user(session) is session.user


class Store:
    def __init__(self, result):
        self.result = result

    def store_access(self, project_id, req):
        return self.result


@pytest.mark.parametrize("result", [None, object(), StoreAccess(UUID(int=0), "synthetic", "owned", "role"),
                                    StoreAccess(uuid4(), "", "owned", "role"),
                                    StoreAccess(uuid4(), "synthetic", "", "role"),
                                    StoreAccess(uuid4(), "synthetic", "owned", "")])
def test_invalid_store_capability_refuses_without_ambient_configuration(result):
    with override_settings(SCITEX_PROJECT_STORE=Store(result)):
        with pytest.raises(CapabilityUnavailable):
            store_access(request(), "owned")


def test_private_store_capability_does_not_print_its_connection():
    capability = StoreAccess(uuid4(), "synthetic-private-connection", "owned", "synthetic_role")
    with override_settings(SCITEX_PROJECT_STORE=Store(capability)):
        assert store_access(request(), "owned") is capability
    assert capability.dsn not in repr(capability)


def test_local_storage_and_store_require_an_explicit_project(tmp_path):
    (tmp_path / "owned").mkdir()
    (tmp_path / ".hidden").mkdir()
    tenant = uuid4()
    with override_settings(SCITEX_LOCAL_PROJECT_ROOT=str(tmp_path), SCITEX_LOCAL_PROJECT_STORES={
            "owned": {"tenant_id": str(tenant), "dsn": "synthetic-private-connection",
                      "project_scope": "owned", "owner_role": "synthetic_role"}}):
        storage = LocalProjectStorage()
        assert storage.project_path("owned", request()) == str(tmp_path / "owned")
        assert storage.project_path(".hidden", request()) is None
        assert storage.project_path("../outside", request()) is None
        assert LocalProjectStore().store_access("owned", request()).tenant_id == tenant
        with pytest.raises(CapabilityUnavailable):
            LocalProjectStore().store_access("unknown", request())
    with override_settings(SCITEX_LOCAL_PROJECT_ROOT=str(tmp_path), SCITEX_LOCAL_PROJECT_STORES={}):
        with pytest.raises(CapabilityUnavailable):
            LocalProjectStore().store_access("owned", request())
