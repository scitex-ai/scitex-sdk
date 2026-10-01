"""Resource authority must not change a newer navigation selection."""
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings

from scitex_sdk.app.project_context import (
    STATE_DENIED,
    STATE_OK,
    STATE_UNAVAILABLE,
    resolve_active_project,
)
from scitex_sdk.host import AccessError, project_access
from scitex_sdk.ui.project_scope import ProjectEntry

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", DATABASES={}, INSTALLED_APPS=[])


class Projects:
    def __init__(self):
        self.selected = "beta"
        self.selections = []
        self.list_calls = 0
        self.fail_remember = False

    def list_projects(self, request):
        self.list_calls += 1
        return [ProjectEntry("alpha", "Alpha"), ProjectEntry("beta", "Beta")]

    def last_visited(self, request):
        return self.selected

    def remember(self, request, project_id):
        if self.fail_remember:
            raise RuntimeError("Synthetic persistence unavailable")
        self.selected = project_id
        self.selections.append(project_id)


class Storage:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.writable = True

    def project_path(self, project_id, request):
        self.calls.append(project_id)
        return self.root / project_id

    def can_write(self, project_id, request):
        return self.writable


@pytest.fixture
def hosted(tmp_path, monkeypatch):
    projects, storage = Projects(), Storage(tmp_path)
    monkeypatch.setitem(globals(), "_projects", projects)
    with override_settings(
        SCITEX_APP_MODE="hub", SCITEX_PROJECT_PROVIDER=__name__ + "._projects",
        SCITEX_PROJECT_STORAGE=storage,
    ):
        yield projects, storage


def request(project="alpha", authenticated=True):
    req = RequestFactory().get("/resource/", {"project": project})
    req.user = SimpleNamespace(is_authenticated=authenticated)
    return req


def _attempt_project_access(req, **options):
    try:
        return project_access(req, **options)
    except AccessError as failure:
        return failure


def test_late_resource_uses_its_own_project_identity(hosted):
    # Arrange
    req = request()
    # Act
    result = project_access(req, remember=False)
    # Assert
    assert result.id == "alpha"


def test_late_resource_uses_its_own_authorized_workspace(hosted):
    # Arrange
    _, storage = hosted
    # Act
    result = project_access(request(), remember=False)
    # Assert
    assert result.root == storage.root / "alpha"


def test_late_resource_keeps_the_newer_navigation_selection(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    project_access(request(), remember=False)
    # Assert
    assert projects.selected == "beta"


def test_late_resource_does_not_persist_a_navigation_selection(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    project_access(request(), remember=False)
    # Assert
    assert projects.selections == []


def test_navigation_keeps_the_requested_project_identity(hosted):
    # Arrange
    req = request()
    # Act
    result = project_access(req)
    # Assert
    assert result.id == "alpha"


def test_navigation_keeps_the_existing_default_selection(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    project_access(request())
    # Assert
    assert projects.selected == "alpha"


def test_navigation_keeps_the_existing_default_persistence(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    project_access(request())
    # Assert
    assert projects.selections == ["alpha"]


def test_denied_resource_raises_the_access_error(hosted):
    # Arrange
    req = request("foreign")
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req, remember=False)


def test_denied_resource_reports_not_found_status(hosted):
    # Arrange
    req = request("foreign")
    # Act
    failure = _attempt_project_access(req, remember=False)
    # Assert
    assert failure.status == 404


def test_denied_resource_keeps_the_existing_selection(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    _attempt_project_access(request("foreign"), remember=False)
    # Assert
    assert projects.selected == "beta"


def test_denied_resource_cannot_reach_storage(hosted):
    # Arrange
    _, storage = hosted
    # Act
    _attempt_project_access(request("foreign"), remember=False)
    # Assert
    assert storage.calls == []


def test_anonymous_resource_raises_the_access_error(hosted):
    # Arrange
    req = request(authenticated=False)
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req, remember=False)


def test_anonymous_resource_reports_unauthorized_status(hosted):
    # Arrange
    req = request(authenticated=False)
    # Act
    failure = _attempt_project_access(req, remember=False)
    # Assert
    assert failure.status == 401


def test_anonymous_resource_cannot_reach_the_provider(hosted):
    # Arrange
    projects, _ = hosted
    # Act
    _attempt_project_access(request(authenticated=False), remember=False)
    # Assert
    assert projects.list_calls == 0


def test_anonymous_resource_cannot_reach_storage(hosted):
    # Arrange
    _, storage = hosted
    # Act
    _attempt_project_access(request(authenticated=False), remember=False)
    # Assert
    assert storage.calls == []


def test_resource_write_permission_stays_required(hosted):
    # Arrange
    _, storage = hosted
    storage.writable = False
    req = request()
    # Act
    # Assert
    with pytest.raises(AccessError):
        project_access(req, write=True, remember=False)


def test_resource_write_refusal_reports_forbidden_status(hosted):
    # Arrange
    _, storage = hosted
    storage.writable = False
    # Act
    failure = _attempt_project_access(request(), write=True, remember=False)
    # Assert
    assert failure.status == 403


def test_resource_write_refusal_keeps_the_existing_selection(hosted):
    # Arrange
    projects, storage = hosted
    storage.writable = False
    # Act
    _attempt_project_access(request(), write=True, remember=False)
    # Assert
    assert projects.selected == "beta"


def test_resource_write_refusal_does_not_persist_a_selection(hosted):
    # Arrange
    projects, storage = hosted
    storage.writable = False
    # Act
    _attempt_project_access(request(), write=True, remember=False)
    # Assert
    assert projects.selections == []


def test_persistence_failure_still_refuses_navigation():
    # Arrange
    provider = Projects()
    provider.fail_remember = True
    # Act
    result = resolve_active_project(request(), provider)
    # Assert
    assert result.state == STATE_UNAVAILABLE


def test_persistence_failure_keeps_the_existing_selection():
    # Arrange
    provider = Projects()
    provider.fail_remember = True
    # Act
    resolve_active_project(request(), provider)
    # Assert
    assert provider.selected == "beta"


def test_resource_resolution_succeeds_without_a_selection_write():
    # Arrange
    provider = Projects()
    provider.fail_remember = True
    # Act
    result = resolve_active_project(request(), provider, remember=False)
    # Assert
    assert result.state == STATE_OK


def test_resource_resolution_keeps_the_requested_project_without_a_selection_write():
    # Arrange
    provider = Projects()
    provider.fail_remember = True
    # Act
    result = resolve_active_project(request(), provider, remember=False)
    # Assert
    assert result.project.id == "alpha"


def test_resource_resolution_does_not_overwrite_the_existing_selection():
    # Arrange
    provider = Projects()
    provider.fail_remember = True
    # Act
    resolve_active_project(request(), provider, remember=False)
    # Assert
    assert provider.selected == "beta"


def test_denied_nonpersisting_resolution_reports_denied_state():
    # Arrange
    provider = Projects()
    # Act
    result = resolve_active_project(request("foreign"), provider, remember=False)
    # Assert
    assert result.state == STATE_DENIED


def test_denied_nonpersisting_resolution_keeps_the_existing_selection():
    # Arrange
    provider = Projects()
    # Act
    resolve_active_project(request("foreign"), provider, remember=False)
    # Assert
    assert provider.selected == "beta"


def test_denied_nonpersisting_resolution_does_not_persist_a_fallback():
    # Arrange
    provider = Projects()
    # Act
    resolve_active_project(request("foreign"), provider, remember=False)
    # Assert
    assert provider.selections == []
