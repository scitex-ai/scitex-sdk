"""The URLconf walker over a real host URLconf (tests._api_inventory_urls)."""

import pytest
from django.urls import get_resolver

from scitex_sdk.app.api_inventory._django import (
    apply_rules,
    normalize_path,
    urlconf_entries,
)


@pytest.fixture(scope="module")
def rows():
    found = urlconf_entries(
        get_resolver("tests._api_inventory_urls"),
        plugin_owners={"notes": ("scitex-notes", "leaf")},
        host_packages=("tests",),
    )
    return apply_rules(found)


@pytest.fixture(scope="module")
def by_key(rows):
    return {(r["path"], tuple(r["methods"])): r for r in rows}


def test_a_route_converter_becomes_a_brace_parameter():
    # Arrange
    raw = "api/<int:pk>/"
    # Act
    path = normalize_path(raw)
    # Assert
    assert path == "/api/{pk}/"


def test_a_regex_group_becomes_a_brace_parameter():
    # Arrange
    raw = r"^api/(?P<slug>[\w-]+)/$"
    # Act
    path = normalize_path(raw)
    # Assert
    assert path == "/api/{slug}/"


def test_a_login_required_post_view_is_session_only(by_key):
    # Arrange
    key = ("/api/project/create/", ("POST",))
    # Act
    row = by_key[key]
    # Assert
    assert (
        row["auth"],
        row["permission"],
        row["owner_kind"],
        "API-A001" in row["violations"],
    ) == (
        ["session"],
        "login",
        "hub",
        True,
    )


def test_a_csrf_exempt_anonymous_write_is_found(by_key):
    # Arrange
    key = ("/api/hooks/open/", ("POST",))
    # Act
    row = by_key[key]
    # Assert
    assert (
        row["auth"],
        row["csrf_exempt"],
        {"API-A001", "API-A004"} <= set(row["violations"]),
    ) == (["none"], True, True)


def test_a_superuser_view_inside_an_include_keeps_its_methods(by_key):
    # Arrange
    key = ("/api/tools/{pk}/", ("DELETE", "GET"))
    # Act
    row = by_key[key]
    # Assert
    assert row["permission"] == "superuser"


def test_an_ungated_view_is_public(by_key):
    # Arrange
    key = ("/api/status/", ("ANY",))
    # Act
    row = by_key[key]
    # Assert
    assert row["auth"] == ["none"]


def test_an_inline_user_check_counts_as_login(by_key):
    # Arrange
    key = ("/api/me/check/", ("ANY",))
    # Act
    row = by_key[key]
    # Assert
    assert row["permission"] == "login"


def test_a_login_mixin_view_is_a_session_class_view(by_key):
    # Arrange
    key = ("/apps/dash/api/summary/", ("GET",))
    # Act
    row = by_key[key]
    # Assert
    assert (row["auth"], row["view_kind"]) == (["session"], "class")


def test_contract_routes_are_owned_by_the_declaring_leaf(rows):
    # Arrange
    contract = [r for r in rows if r["contract"] and r["plugin"]]
    # Act
    owners = {(r["owner_package"], r["versioned"], tuple(r["auth"])) for r in contract}
    # Assert
    assert owners == {("scitex-notes", True, ("contract",))}


def test_html_pages_are_kept_but_not_judged(rows):
    # Arrange
    home = next(r for r in rows if r["path"] == "/")
    # Act
    verdict = (home["kind"], home["violations"])
    # Assert
    assert verdict == ("page", [])
