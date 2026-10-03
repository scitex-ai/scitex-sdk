"""Optional tagged-scope capability: user/null or canonical project/id.

Legacy POST {id} behavior is preserved byte-for-byte on every provider; the
tagged {scope, id} payload commits only through a supporting provider's one
remember_scope entrypoint. Unselected GET omits current_scope; stale, unknown
or null scopes are never accepted as All.
"""

from __future__ import annotations

import json

import pytest
from django.test import RequestFactory

from scitex_sdk.ui import project_scope as scope


class LegacyProvider:
    def __init__(self):
        # Arrange
        self.stored = None
        self.remembered = []

    def list_projects(self, request):
        # Arrange
        return [scope.ProjectEntry("alpha", "Alpha"), scope.ProjectEntry("beta", "Beta")]

    def last_visited(self, request):
        # Arrange
        return self.stored

    def remember(self, request, project_id):
        # Arrange
        self.remembered.append(project_id)
        self.stored = project_id


class ScopedProvider(LegacyProvider):
    def __init__(self):
        # Arrange
        super().__init__()
        self.tag = None
        self.scope_commits = []

    def current_scope(self, request):
        # Arrange
        return self.tag

    def remember_scope(self, request, selection):
        # Arrange
        self.scope_commits.append(selection)
        self.tag = selection
        self.stored = selection.id


def _post(view, payload):
    # Arrange
    return view(RequestFactory().post("/", data=json.dumps(payload), content_type="application/json"))


def _body(response):
    # Arrange
    return json.loads(response.content.decode())


def test_legacy_post_unchanged_on_legacy_provider():
    # Arrange
    provider = LegacyProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"id": "alpha"})
    # Assert
    assert response.status_code == 200 and _body(response) == {"current": "alpha"} and provider.remembered == ["alpha"]


def test_legacy_post_unchanged_on_scoped_provider():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"id": "beta"})
    # Assert
    assert response.status_code == 200 and _body(response) == {"current": "beta"} and provider.remembered == ["beta"] and provider.scope_commits == []


def test_tagged_user_refused_without_capability():
    # Arrange
    provider = LegacyProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"scope": "user", "id": None})
    # Assert
    assert response.status_code == 403 and provider.stored is None


def test_tagged_user_commits_through_one_entrypoint():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"scope": "user", "id": None})
    # Assert
    assert response.status_code == 200 and _body(response) == {"current": None, "current_scope": "user"} and provider.scope_commits == [scope.ProjectSelection(scope="user", id=None)] and provider.remembered == []


def test_tagged_project_commits_canonical_pair():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"scope": "project", "id": "alpha"})
    # Assert
    assert response.status_code == 200 and _body(response) == {"current": "alpha", "current_scope": "project"} and provider.scope_commits == [scope.ProjectSelection(scope="project", id="alpha")]


def test_tagged_inaccessible_project_refused_without_side_effects():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    response = _post(view, {"scope": "project", "id": "someone-elses"})
    # Assert
    assert response.status_code == 403 and provider.tag is None and provider.scope_commits == []


def test_malformed_tagged_payloads_refused():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    statuses = [_post(view, payload).status_code for payload in ({"scope": "bogus"}, {"scope": "user", "id": "alpha"}, {"scope": "project", "id": ""}, {"scope": "project"}, "not-an-object", {"id": None})]
    # Assert
    assert statuses == [403, 403, 403, 403, 403, 403] and provider.tag is None


def test_get_omits_scope_when_unselected():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    # Act
    body = _body(view(RequestFactory().get("/")))
    # Assert
    assert body["current"] is None and "current_scope" not in body and body["allow_user_scope"] is True and [p["id"] for p in body["projects"]] == ["alpha", "beta"]


def test_get_reflects_committed_tag():
    # Arrange
    provider = ScopedProvider()
    view = scope.scoped_project_listing_view(provider)
    _post(view, {"scope": "user", "id": None})
    # Act
    body = _body(view(RequestFactory().get("/")))
    # Assert
    assert body["current"] is None and body["current_scope"] == "user"


def test_get_unselected_forces_null_despite_stale_legacy_projection():
    # Arrange
    provider = ScopedProvider()
    provider.remember(None, "alpha")
    provider.tag = None
    view = scope.scoped_project_listing_view(provider)
    # Act
    body = _body(view(RequestFactory().get("/")))
    # Assert
    assert body["current"] is None and "current_scope" not in body


def test_selection_validation_rejects_bad_pairs():
    # Arrange
    bad = [lambda: scope.ProjectSelection(scope="bogus"), lambda: scope.ProjectSelection(scope="user", id="alpha"), lambda: scope.ProjectSelection(scope="project", id="")]
    # Act
    refused = 0
    for make in bad:
        try:
            make()
        except ValueError:
            refused += 1
    # Assert
    assert refused == 3


def test_capability_detection_keeps_protocol_unchanged():
    # Arrange
    legacy = LegacyProvider()
    scoped = ScopedProvider()
    legacy_body = _body(scope.scoped_project_listing_view(legacy)(RequestFactory().get("/")))
    # Act
    pass
    # Assert
    assert scope.supports_scoped_capability(scoped) and not scope.supports_scoped_capability(legacy) and legacy_body["allow_user_scope"] is False and "current_scope" not in legacy_body
