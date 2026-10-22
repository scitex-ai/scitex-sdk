"""Optional host aliases never replace request-scoped project authority."""

from types import SimpleNamespace

import pytest
from django.test import RequestFactory, override_settings

from scitex_sdk import host
from scitex_sdk.app import project_context as context
from scitex_sdk.ui import project_scope as scope


class Provider:
    def __init__(self, result="alice/alpha"):
        self.result = result
        self.stored = "alice/beta"
        self.calls = []
        self.remembered = []
        self.reads = []

    def list_projects(self, request):
        self.reads.append("list")
        return [
            scope.ProjectEntry("alice/alpha", "Alpha"),
            scope.ProjectEntry("alice/beta", "Beta"),
        ]

    def last_visited(self, request):
        self.reads.append("last")
        return self.stored

    def remember(self, request, project_id):
        self.remembered.append(project_id)
        self.stored = project_id

    def canonical_project_id(self, request, selector):
        self.calls.append(selector)
        return self.result


def request():
    return SimpleNamespace(GET={}, user=SimpleNamespace(is_authenticated=True))


@pytest.fixture
def _use_provider():
    # Arrange — install a hand-written fake as the host provider without
    # the monkeypatch fixture: explicit save/restore around the test.
    prior = scope.host_project_provider

    def use(provider):
        scope.host_project_provider = lambda: provider  # noqa: E731

    try:
        yield use
    finally:
        scope.host_project_provider = prior


def _recording_factory():
    # Arrange helper — a provider factory recording its invocations.
    provider = Provider()
    calls = []

    def factory(req):
        calls.append(req)
        return provider

    factory.calls = calls  # type: ignore[attr-defined]
    factory.provider = provider  # type: ignore[attr-defined]
    return factory


def test_alias_resolves_listed_canonical_id():
    # Arrange
    provider = Provider()
    # Act
    result = context.resolve_active_project(request(), provider, "17")
    # Assert
    assert result.ok and result.project.id == "alice/alpha"


def test_alias_consults_provider_once_and_remembers():
    # Arrange
    provider = Provider()
    # Act
    context.resolve_active_project(request(), provider, "17")
    # Assert
    assert provider.calls == ["17"] and provider.remembered == ["alice/alpha"]


def test_canonical_selector_returns_without_normalization():
    # Arrange
    provider = Provider("not-listed")
    # Act
    result = context.resolve_active_project(request(), provider, "alice/alpha")
    # Assert
    assert result.ok and result.project.id == "alice/alpha"


def test_canonical_selector_skips_optional_method():
    # Arrange
    provider = Provider("not-listed")
    # Act
    context.resolve_active_project(request(), provider, "alice/alpha")
    # Assert
    assert provider.calls == [] and provider.remembered == ["alice/alpha"]


def test_absent_optional_method_denies_numeric_selector():
    # Arrange
    provider = Provider()
    provider.canonical_project_id = None
    # Act
    result = context.resolve_active_project(request(), provider, "17")
    # Assert
    assert result.state == context.STATE_DENIED


def test_absent_optional_method_never_remembers():
    # Arrange
    provider = Provider()
    provider.canonical_project_id = None
    # Act
    context.resolve_active_project(request(), provider, "17")
    # Assert
    assert provider.stored == "alice/beta" and provider.remembered == []


@pytest.mark.parametrize(
    "returned", [None, "bob/private", "bob/public", "unknown", 17, ["alice/alpha"]]
)
def test_unlisted_or_invalid_alias_result_denies(returned):
    # Arrange
    provider = Provider(returned)
    # Act
    result = context.resolve_active_project(request(), provider, "17")
    # Assert
    assert result.state == context.STATE_DENIED


@pytest.mark.parametrize(
    "returned", [None, "bob/private", "bob/public", "unknown", 17, ["alice/alpha"]]
)
def test_unlisted_or_invalid_alias_never_resolves(returned):
    # Arrange
    provider = Provider(returned)
    # Act
    resolved = scope.resolve_project(request(), provider, "17")
    # Assert
    assert resolved is None


@pytest.mark.parametrize(
    "returned", [None, "bob/private", "bob/public", "unknown", 17, ["alice/alpha"]]
)
def test_unlisted_or_invalid_alias_never_remembers(returned):
    # Arrange
    provider = Provider(returned)
    # Act
    context.resolve_active_project(request(), provider, "17")
    # Assert
    assert provider.stored == "alice/beta" and provider.remembered == []


def test_resource_alias_without_remember_keeps_stored():
    # Arrange
    provider = Provider()
    # Act
    result = context.resolve_active_project(request(), provider, "17", remember=False)
    # Assert
    assert result.ok and result.project.id == "alice/alpha"


def test_resource_alias_without_remember_never_writes():
    # Arrange
    provider = Provider()
    # Act
    context.resolve_active_project(request(), provider, "17", remember=False)
    # Assert
    assert provider.stored == "alice/beta" and provider.remembered == []


def test_post_response_carries_canonical_identity():
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(provider)(posted)
    # Assert
    assert response.status_code == 200 and response.content == b'{"current": "alice/alpha"}'


def test_post_response_remembers_canonical_identity():
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(provider)(posted)
    # Assert
    assert provider.remembered == ["alice/alpha"]


@pytest.mark.parametrize(
    "selected", [None, "", 0, 0.0, False, True, [], {}, ["17"], {"id": "17"}, 17]
)
def test_listing_refuses_invalid_selectors_status(selected):
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": selected}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(provider)(posted)
    # Assert
    assert response.status_code == 403


@pytest.mark.parametrize(
    "selected", [None, "", 0, 0.0, False, True, [], {}, ["17"], {"id": "17"}, 17]
)
def test_listing_refuses_invalid_selectors_body(selected):
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": selected}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(provider)(posted)
    # Assert
    assert response.content == b'{"error": "project not accessible"}'


@pytest.mark.parametrize(
    "selected", [None, "", 0, 0.0, False, True, [], {}, ["17"], {"id": "17"}, 17]
)
def test_listing_refuses_invalid_selectors_without_reads(selected):
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": selected}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(provider)(posted)
    # Assert
    assert provider.reads == [] and provider.calls == []


@pytest.mark.parametrize(
    "selected", [None, "", 0, 0.0, False, True, [], {}, ["17"], {"id": "17"}, 17]
)
def test_listing_refuses_invalid_selectors_without_remember(selected):
    # Arrange
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": selected}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(provider)(posted)
    # Assert
    assert provider.remembered == [] and provider.stored == "alice/beta"


@pytest.mark.parametrize(
    "body", [b"", b"{", b"not-json", b"\xff", b"[]", b"null", b"true", b"17", b'"17"', b"{}"]
)
def test_listing_refuses_malformed_body_status(body):
    # Arrange
    posted = RequestFactory().generic(
        "POST", "/scope/", body, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(_recording_factory())(posted)
    # Assert
    assert response.status_code == 403


@pytest.mark.parametrize(
    "body", [b"", b"{", b"not-json", b"\xff", b"[]", b"null", b"true", b"17", b'"17"', b"{}"]
)
def test_listing_refuses_malformed_body_without_factory_call(body):
    # Arrange
    factory = _recording_factory()
    posted = RequestFactory().generic(
        "POST", "/scope/", body, content_type="application/json"
    )
    # Act
    scope.project_listing_view(factory)(posted)
    # Assert
    assert factory.calls == []


def test_listing_denied_alias_status():
    # Arrange
    provider = Provider("bob/private")
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(provider)(posted)
    # Assert
    assert response.status_code == 403


def test_listing_denied_alias_reads_before_refusing():
    # Arrange
    provider = Provider("bob/private")
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(provider)(posted)
    # Assert
    assert provider.reads == ["list"] and provider.calls == ["17"]


def test_listing_denied_alias_never_remembers():
    # Arrange
    provider = Provider("bob/private")
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(provider)(posted)
    # Assert
    assert provider.remembered == [] and provider.stored == "alice/beta"


def test_listing_valid_id_status():
    # Arrange
    factory = _recording_factory()
    posted = RequestFactory().post(
        "/scope/", {"id": "alice/alpha"}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(factory)(posted)
    # Assert
    assert response.status_code == 200


def test_listing_valid_id_body():
    # Arrange
    factory = _recording_factory()
    posted = RequestFactory().post(
        "/scope/", {"id": "alice/alpha"}, content_type="application/json"
    )
    # Act
    response = scope.project_listing_view(factory)(posted)
    # Assert
    assert response.content == b'{"current": "alice/alpha"}'


def test_listing_valid_id_consults_factory_once():
    # Arrange
    factory = _recording_factory()
    posted = RequestFactory().post(
        "/scope/", {"id": "alice/alpha"}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(factory)(posted)
    # Assert
    assert factory.calls == [posted]


def test_listing_valid_id_remembers_without_normalization():
    # Arrange
    factory = _recording_factory()
    posted = RequestFactory().post(
        "/scope/", {"id": "alice/alpha"}, content_type="application/json"
    )
    # Act
    scope.project_listing_view(factory)(posted)
    # Assert
    assert factory.provider.calls == [] and factory.provider.remembered == ["alice/alpha"]


def test_navigation_without_selection_falls_back_to_stored():
    # Arrange
    provider = Provider()
    # Act
    resolved = scope.resolve_project(request(), provider)
    # Assert
    assert resolved == "alice/beta"


def test_navigation_without_selection_reads_list_and_last():
    # Arrange
    provider = Provider()
    # Act
    scope.resolve_project(request(), provider)
    # Assert
    assert provider.reads == ["list", "last"] and provider.calls == []


def test_navigation_without_selection_never_remembers():
    # Arrange
    provider = Provider()
    # Act
    scope.resolve_project(request(), provider)
    # Assert
    assert provider.remembered == [] and provider.stored == "alice/beta"


def test_provider_fault_is_unavailable():
    # Arrange
    provider = Provider()

    def unavailable(request, selector):
        raise RuntimeError("synthetic provider outage")

    provider.canonical_project_id = unavailable
    # Act
    result = context.resolve_active_project(request(), provider, "17")
    # Assert
    assert result.state == context.STATE_UNAVAILABLE


def test_provider_fault_never_remembers():
    # Arrange
    provider = Provider()

    def unavailable(request, selector):
        raise RuntimeError("synthetic provider outage")

    provider.canonical_project_id = unavailable
    # Act
    context.resolve_active_project(request(), provider, "17")
    # Assert
    assert provider.remembered == []


def test_no_configured_provider_remains_unavailable():
    # Arrange
    req = request()
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=""):
        result = context.resolve_active_project(req, explicit="17")
    # Assert
    assert result.state == context.STATE_UNAVAILABLE


def test_host_storage_resolves_canonical_id(_use_provider, tmp_path):
    # Arrange
    provider = Provider()
    _use_provider(provider)
    calls = []
    storage = SimpleNamespace(
        project_path=lambda key, req: calls.append(key) or tmp_path,
        can_write=lambda key, req: calls.append(key) or True,
    )
    req = request()
    req.GET["project"] = "17"
    # Act
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        access = host.project_access(req, write=True, remember=False)
    # Assert
    assert access.id == "alice/alpha" and calls == ["alice/alpha"] * 3


def test_host_storage_never_remembers_listing(_use_provider, tmp_path):
    # Arrange
    provider = Provider()
    _use_provider(provider)
    storage = SimpleNamespace(
        project_path=lambda key, req: tmp_path,
        can_write=lambda key, req: True,
    )
    req = request()
    req.GET["project"] = "17"
    # Act
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        host.project_access(req, write=True, remember=False)
    # Assert
    assert provider.remembered == []


def test_host_denied_alias_raises_access_error(_use_provider):
    # Arrange
    _use_provider(Provider("bob/private"))
    storage = SimpleNamespace(
        project_path=lambda *args: pytest.fail("denied alias reached storage")
    )
    req = request()
    req.GET["project"] = "17"
    # Act
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        raised = None
        try:
            host.project_access(req)
        except host.AccessError as exc:
            raised = exc
    # Assert
    assert isinstance(raised, host.AccessError)


def test_host_denied_alias_status_is_404(_use_provider):
    # Arrange
    _use_provider(Provider("bob/private"))
    storage = SimpleNamespace(
        project_path=lambda *args: pytest.fail("denied alias reached storage")
    )
    req = request()
    req.GET["project"] = "17"
    # Act
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        raised = None
        try:
            host.project_access(req)
        except host.AccessError as exc:
            raised = exc
    # Assert
    assert raised is not None and raised.status == 404


def test_host_denied_alias_never_remembers(_use_provider):
    # Arrange
    provider = Provider("bob/private")
    _use_provider(provider)
    storage = SimpleNamespace(
        project_path=lambda *args: pytest.fail("denied alias reached storage")
    )
    req = request()
    req.GET["project"] = "17"
    # Act
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        try:
            host.project_access(req)
        except host.AccessError:
            pass
    # Assert
    assert provider.remembered == []
