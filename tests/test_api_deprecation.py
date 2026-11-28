"""API-H003 headers on legacy routes, through real Django middleware and URLs."""

from datetime import date

from django.http import JsonResponse
from django.test import Client, override_settings
from django.urls import path

from scitex_sdk.app.api_deprecation import add_months, headers_for, load


def legacy_list(request):
    return JsonResponse({"projects": []})


def current_list(request):
    return JsonResponse({"data": []})


urlpatterns = [
    path("api/project/list/", legacy_list),
    path("api/v1/hub/projects", current_list),
]

DEPRECATIONS = [
    {
        "pattern": r"^/api/project/list/$",
        "deprecated_at": "2026-11-28",
        "sunset_months_after_beta": 6,
        "successor": "/api/v1/hub/projects",
    }
]
SETTINGS = dict(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["scitex_sdk.app.api_deprecation.LegacyApiDeprecationMiddleware"],
    SCITEX_API_DEPRECATIONS=DEPRECATIONS,
)


def test_a_legacy_route_carries_deprecation_sunset_and_link():
    # Arrange
    with override_settings(**SETTINGS, SCITEX_API_BETA_LAUNCH_DATE="2027-01-31"):
        # Act
        response = Client().get("/api/project/list/")
    # Assert
    assert (response["Deprecation"], response["Sunset"], response["Link"]) == (
        "@1795824000",
        "Sat, 31 Jul 2027 00:00:00 GMT",
        '</api/v1/hub/projects>; rel="successor-version", '
        '<https://scitex.ai/docs/api/deprecations>; rel="deprecation"',
    )


def test_without_a_beta_date_no_sunset_is_promised():
    # Arrange
    with override_settings(**SETTINGS, SCITEX_API_BETA_LAUNCH_DATE=None):
        # Act
        response = Client().get("/api/project/list/")
    # Assert
    assert (response.has_header("Deprecation"), response.has_header("Sunset")) == (
        True,
        False,
    )


def test_a_v1_route_is_not_deprecated():
    # Arrange
    with override_settings(**SETTINGS, SCITEX_API_BETA_LAUNCH_DATE="2027-01-31"):
        # Act
        response = Client().get("/api/v1/hub/projects")
    # Assert
    assert response.has_header("Deprecation") is False


def test_the_response_body_is_unchanged():
    # Arrange
    with override_settings(**SETTINGS, SCITEX_API_BETA_LAUNCH_DATE="2027-01-31"):
        # Act
        response = Client().get("/api/project/list/")
    # Assert
    assert response.json() == {"projects": []}


def test_months_are_added_by_calendar_and_clamped():
    # Arrange
    start = date(2027, 8, 31)
    # Act
    end = add_months(start, 6)
    # Assert
    assert end == date(2028, 2, 29)


def test_a_longer_window_is_per_entry():
    # Arrange
    entries = [
        dict(
            DEPRECATIONS[0],
            pattern=r"^/api/v1/scholar/search/$",
            sunset_months_after_beta=12,
        )
    ]
    deprecations, beta = load(entries, "2027-01-31")
    # Act
    headers = headers_for("/api/v1/scholar/search/", deprecations, beta)
    # Assert
    assert headers["Sunset"] == "Mon, 31 Jan 2028 00:00:00 GMT"
