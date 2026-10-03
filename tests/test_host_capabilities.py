"""Host authority and local capabilities against only synthetic workspaces."""
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from django.test import RequestFactory, override_settings

from scitex_sdk.host import (
    AccessError,
    CapabilityUnavailable,
    ProjectAccess,
    StoreAccess,
    authenticated_user,
    project_access,
    store_access,
)
from scitex_sdk.local import LocalProjectStorage, LocalProjectStore
from scitex_sdk.ui.project_scope import ProjectEntry


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
    with override_settings(
        SCITEX_APP_MODE="hub", SCITEX_PROJECT_PROVIDER=__name__ + "._projects",
        SCITEX_PROJECT_STORAGE=storage, SCITEX_PROJECT_STORE=None,
    ):
        yield projects, storage


@pytest.fixture
def confined_project(tmp_path):
    root, foreign = tmp_path / "owned", tmp_path / "foreign"
    root.mkdir()
    foreign.mkdir()
    (root / "foreign-link").symlink_to(foreign, target_is_directory=True)
    return ProjectAccess("owned", "Owned", root)


@pytest.fixture
def local_project(tmp_path):
    (tmp_path / "owned").mkdir()
    (tmp_path / ".hidden").mkdir()
    tenant = uuid4()
    with override_settings(
        SCITEX_LOCAL_PROJECT_ROOT=str(tmp_path),
        SCITEX_LOCAL_PROJECT_STORES={
            "owned": {"tenant_id": str(tenant), "dsn": "synthetic-private-connection",
                      "project_scope": "owned", "owner_role": "synthetic_role"},
        },
    ):
        yield tmp_path, tenant


def request(authenticated=True, project="owned"):
    req = RequestFactory().get("/", {"project": project})
    req.user = SimpleNamespace(is_authenticated=authenticated)
    return req


def _attempt_project_access(req, **options):
    try:
        return project_access(req, **options)
    except AccessError as failure:
        return failure


def test_anonymous_host_access_raises_the_access_error(hosted):
    # Arrange
    req = request(False)
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req)


def test_anonymous_host_access_reports_unauthorized_status(hosted):
    # Arrange
    req = request(False)
    # Act
    failure = _attempt_project_access(req)
    # Assert
    assert failure.status == 401


def test_anonymous_host_access_does_not_change_project_selection(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    _attempt_project_access(request(False))
    # Assert
    assert projects.selections == []


def test_anonymous_host_access_does_not_reach_storage(hosted):
    # Arrange
    _, storage = hosted
    # Act
    _attempt_project_access(request(False))
    # Assert
    assert storage.calls == []


def test_denied_explicit_project_raises_the_access_error(hosted):
    # Arrange
    req = request(project="foreign")
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req)


def test_denied_explicit_project_reports_not_found_status(hosted):
    # Arrange
    req = request(project="foreign")
    # Act
    failure = _attempt_project_access(req)
    # Assert
    assert failure.status == 404


def test_denied_explicit_project_keeps_the_existing_project(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    _attempt_project_access(request(project="foreign"))
    # Assert
    assert projects.selected == "owned"


def test_denied_explicit_project_does_not_persist_a_fallback(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    _attempt_project_access(request(project="foreign"))
    # Assert
    assert projects.selections == []


def test_denied_explicit_project_does_not_reach_storage(hosted):
    # Arrange
    _, storage = hosted
    # Act
    _attempt_project_access(request(project="foreign"))
    # Assert
    assert storage.calls == []


@pytest.mark.parametrize("setting", ["SCITEX_PROJECT_PROVIDER", "SCITEX_PROJECT_STORAGE"])
def test_missing_host_capability_has_no_local_fallback(hosted, setting):
    # Arrange
    req = request()
    # Act
    # Assert
    with override_settings(**{setting: None}), pytest.raises(CapabilityUnavailable):
        project_access(req)


@pytest.mark.parametrize("writable", [False, None, 0, 1, "true", "false"])
def test_write_authority_requires_literal_true(hosted, writable):
    # Arrange
    _, storage = hosted
    storage.writable = writable
    req = request()
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req, write=True)


@pytest.mark.parametrize("writable", [False, None, 0, 1, "true", "false"])
def test_nonliteral_write_authority_reports_forbidden_status(hosted, writable):
    # Arrange
    _, storage = hosted
    storage.writable = writable
    # Act
    failure = _attempt_project_access(request(), write=True)
    # Assert
    assert failure.status == 403


def test_authorized_project_is_the_host_workspace(hosted):
    # Arrange
    _, storage = hosted
    # Act
    result = project_access(request(), write=True)
    # Assert
    assert result == ProjectAccess("owned", "Owned", storage.root.resolve(), True)


def test_project_path_accepts_a_confined_file(confined_project):
    # Arrange
    capability = confined_project
    # Act
    result = capability.path("valid.txt")
    # Assert
    assert result == capability.root / "valid.txt"


@pytest.mark.parametrize("relative", ["../foreign/data.txt", "foreign-link/data.txt"])
def test_project_path_refuses_traversal_and_foreign_symlink(confined_project, relative):
    # Arrange
    capability = confined_project
    # Act
    # Assert
    with pytest.raises(AccessError):
        capability.path(relative)


def test_anonymous_authentication_has_no_implicit_host_provider():
    # Arrange
    anonymous = request(False)
    # Act
    with override_settings(SCITEX_API_AUTHENTICATOR=None):
        result = authenticated_user(anonymous)
    # Assert
    assert result is None


def test_authenticator_returns_only_the_explicit_host_provider_value():
    # Arrange
    anonymous = request(False)
    expected = object()
    # Act
    with override_settings(SCITEX_API_AUTHENTICATOR=lambda req: expected):
        result = authenticated_user(anonymous)
    # Assert
    assert result is expected


def test_authenticated_session_user_remains_available():
    # Arrange
    session = request()
    # Act
    result = authenticated_user(session)
    # Assert
    assert result is session.user


class Store:
    def __init__(self, result):
        self.result = result

    def store_access(self, project_id, req):
        return self.result


@pytest.mark.parametrize("result", [
    None, object(), StoreAccess(UUID(int=0), "synthetic", "owned", "role"),
    StoreAccess(uuid4(), "", "owned", "role"),
    StoreAccess(uuid4(), "synthetic", "", "role"),
    StoreAccess(uuid4(), "synthetic", "owned", ""),
])
def test_invalid_store_capability_refuses_without_ambient_configuration(result):
    # Arrange
    req = request()
    # Act
    # Assert
    with override_settings(SCITEX_PROJECT_STORE=Store(result)), pytest.raises(CapabilityUnavailable):
        store_access(req, "owned")


def test_private_store_capability_is_returned_by_identity():
    # Arrange
    capability = StoreAccess(uuid4(), "synthetic-private-connection", "owned", "synthetic_role")
    # Act
    with override_settings(SCITEX_PROJECT_STORE=Store(capability)):
        result = store_access(request(), "owned")
    # Assert
    assert result is capability


def test_private_store_capability_does_not_print_its_connection():
    # Arrange
    capability = StoreAccess(uuid4(), "synthetic-private-connection", "owned", "synthetic_role")
    # Act
    displayed = repr(capability)
    # Assert
    assert capability.dsn not in displayed


def test_local_storage_resolves_only_the_explicit_owned_project(local_project):
    # Arrange
    root, _ = local_project
    storage = LocalProjectStorage()
    # Act
    result = storage.project_path("owned", request())
    # Assert
    assert result == str(root / "owned")


@pytest.mark.parametrize("project", [".hidden", "../outside"])
def test_local_storage_refuses_hidden_and_traversing_projects(local_project, project):
    # Arrange
    storage = LocalProjectStorage()
    # Act
    result = storage.project_path(project, request())
    # Assert
    assert result is None


def test_local_store_preserves_the_explicit_tenant(local_project):
    # Arrange
    _, tenant = local_project
    # Act
    result = LocalProjectStore().store_access("owned", request())
    # Assert
    assert result.tenant_id == tenant


def test_local_store_refuses_an_unknown_project(local_project):
    # Arrange
    store = LocalProjectStore()
    req = request()
    # Act
    # Assert
    with pytest.raises(CapabilityUnavailable):
        store.store_access("unknown", req)


def test_local_store_has_no_fallback_for_an_unconfigured_owned_project(tmp_path):
    # Arrange
    req = request()
    # Act
    # Assert
    with (
        override_settings(SCITEX_LOCAL_PROJECT_ROOT=str(tmp_path), SCITEX_LOCAL_PROJECT_STORES={}),
        pytest.raises(CapabilityUnavailable),
    ):
        LocalProjectStore().store_access("owned", req)


def test_write_without_grant_refused_before_path_resolution(hosted):
    # Arrange
    _, storage = hosted
    storage.writable = False
    req = request()
    # Act
    failure = _attempt_project_access(req, write=True)
    # Assert
    assert failure.status == 403 and storage.calls == []


def test_write_to_missing_project_reports_not_found_before_storage(hosted):
    # Arrange
    _, storage = hosted
    storage.writable = False
    req = request(project="missing")
    # Act
    failure = _attempt_project_access(req, write=True)
    # Assert
    assert failure.status == 404 and storage.calls == []


def test_write_with_grant_resolves_path(hosted):
    # Arrange
    req = request()
    # Act
    access = project_access(req, write=True)
    # Assert
    assert access.can_write is True and access.id == "owned"


def test_read_without_grant_still_resolves_path(hosted):
    # Arrange
    _, storage = hosted
    storage.writable = False
    req = request()
    # Act
    access = project_access(req)
    # Assert
    assert access.can_write is False and storage.calls == ["owned"]
