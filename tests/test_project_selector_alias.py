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


def test_alias_returns_and_remembers_only_the_listed_canonical_id():
    provider = Provider()
    result = context.resolve_active_project(request(), provider, "17")
    assert result.ok and result.project.id == "alice/alpha"
    assert provider.calls == ["17"] and provider.remembered == ["alice/alpha"]


def test_canonical_selector_never_calls_optional_normalization():
    provider = Provider("not-listed")
    result = context.resolve_active_project(request(), provider, "alice/alpha")
    assert result.ok and result.project.id == "alice/alpha"
    assert provider.calls == [] and provider.remembered == ["alice/alpha"]


def test_absent_optional_method_keeps_numeric_selector_denied_without_fallback():
    provider = Provider()
    provider.canonical_project_id = None
    result = context.resolve_active_project(request(), provider, "17")
    assert result.state == context.STATE_DENIED
    assert provider.stored == "alice/beta" and provider.remembered == []


@pytest.mark.parametrize(
    "returned", [None, "bob/private", "bob/public", "unknown", 17, ["alice/alpha"]]
)
def test_unlisted_or_invalid_alias_result_never_grants_access(returned):
    provider = Provider(returned)
    result = context.resolve_active_project(request(), provider, "17")
    assert result.state == context.STATE_DENIED
    assert scope.resolve_project(request(), provider, "17") is None
    assert provider.stored == "alice/beta" and provider.remembered == []


def test_resource_alias_does_not_overwrite_newer_navigation():
    provider = Provider()
    result = context.resolve_active_project(request(), provider, "17", remember=False)
    assert result.ok and result.project.id == "alice/alpha"
    assert provider.stored == "alice/beta" and provider.remembered == []


def test_ui_resolution_and_post_response_use_the_same_canonical_identity():
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    response = scope.project_listing_view(provider)(posted)
    assert (
        response.status_code == 200
        and response.content == b'{"current": "alice/alpha"}'
    )
    assert provider.remembered == ["alice/alpha"]


@pytest.mark.parametrize(
    "selected", [None, "", 0, 0.0, False, True, [], {}, ["17"], {"id": "17"}, 17]
)
def test_listing_refuses_invalid_selectors_before_provider_reads(selected):
    provider = Provider()
    posted = RequestFactory().post(
        "/scope/", {"id": selected}, content_type="application/json"
    )
    response = scope.project_listing_view(provider)(posted)
    assert response.status_code == 403
    assert response.content == b'{"error": "project not accessible"}'
    assert provider.reads == [] and provider.calls == []
    assert provider.remembered == [] and provider.stored == "alice/beta"


@pytest.mark.parametrize(
    "body", [
        b"", b"{", b"not-json", b"\xff", b"[]", b"null", b"true", b"17", b'"17"', b"{}"
    ]
)
def test_listing_refuses_missing_or_malformed_body_before_provider_factory(body):
    provider = Provider()
    factory_calls = []

    def factory(req):
        factory_calls.append(req)
        return provider

    posted = RequestFactory().generic(
        "POST", "/scope/", body, content_type="application/json"
    )
    response = scope.project_listing_view(factory)(posted)
    assert response.status_code == 403
    assert response.content == b'{"error": "project not accessible"}'
    assert factory_calls == [] and provider.reads == [] and provider.calls == []
    assert provider.remembered == [] and provider.stored == "alice/beta"


def test_listing_denied_alias_never_reads_stored_selection_or_remembers():
    provider = Provider("bob/private")
    posted = RequestFactory().post(
        "/scope/", {"id": "17"}, content_type="application/json"
    )
    response = scope.project_listing_view(provider)(posted)
    assert response.status_code == 403
    assert provider.reads == ["list"] and provider.calls == ["17"]
    assert provider.remembered == [] and provider.stored == "alice/beta"


def test_listing_valid_id_resolves_provider_factory_and_remembers():
    provider = Provider("not-listed")
    factory_calls = []

    def factory(req):
        factory_calls.append(req)
        return provider

    posted = RequestFactory().post(
        "/scope/", {"id": "alice/alpha"}, content_type="application/json"
    )
    response = scope.project_listing_view(factory)(posted)
    assert response.status_code == 200
    assert response.content == b'{"current": "alice/alpha"}'
    assert factory_calls == [posted] and provider.reads == ["list"]
    assert provider.calls == [] and provider.remembered == ["alice/alpha"]


def test_navigation_without_selection_keeps_authorized_stored_fallback():
    provider = Provider()
    assert scope.resolve_project(request(), provider) == "alice/beta"
    assert provider.reads == ["list", "last"] and provider.calls == []
    assert provider.remembered == [] and provider.stored == "alice/beta"


def test_provider_fault_is_unavailable_without_remembering():
    provider = Provider()

    def unavailable(request, selector):
        raise RuntimeError("synthetic provider outage")

    provider.canonical_project_id = unavailable
    result = context.resolve_active_project(request(), provider, "17")
    assert result.state == context.STATE_UNAVAILABLE and provider.remembered == []


def test_no_configured_provider_remains_unavailable():
    with override_settings(SCITEX_PROJECT_PROVIDER=""):
        result = context.resolve_active_project(request(), explicit="17")
    assert result.state == context.STATE_UNAVAILABLE


def test_host_storage_sees_only_canonical_authorized_ids(monkeypatch, tmp_path):
    provider = Provider()
    monkeypatch.setattr(scope, "host_project_provider", lambda: provider)
    calls = []
    storage = SimpleNamespace(
        project_path=lambda key, req: calls.append(key) or tmp_path,
        can_write=lambda key, req: calls.append(key) or True,
    )
    req = request()
    req.GET["project"] = "17"
    with override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage):
        access = host.project_access(req, write=True, remember=False)
    assert access.id == "alice/alpha" and calls == ["alice/alpha", "alice/alpha", "alice/alpha"]
    assert provider.remembered == []


def test_host_denied_alias_cannot_consult_storage(monkeypatch):
    provider = Provider("bob/private")
    monkeypatch.setattr(scope, "host_project_provider", lambda: provider)
    storage = SimpleNamespace(
        project_path=lambda *args: pytest.fail("denied alias reached storage")
    )
    req = request()
    req.GET["project"] = "17"
    with (
        override_settings(SCITEX_APP_MODE="hub", SCITEX_PROJECT_STORAGE=storage),
        pytest.raises(host.AccessError) as exc,
    ):
        host.project_access(req)
    assert exc.value.status == 404 and provider.remembered == []
