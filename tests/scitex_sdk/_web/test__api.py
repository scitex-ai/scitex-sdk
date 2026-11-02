"""The real installed SDK Web declaration is discoverable and opt-in only."""

import json

import pytest
from django.test import RequestFactory

from scitex_sdk._web._api import plugin
from scitex_sdk.app._api_contract import scan_web_contract
from scitex_sdk.app.api_mount import AdmissionDenied, admit, resolve_handler
from scitex_sdk.app.api_plugin import discover_api_plugins


def test_installed_reference_requires_explicit_host_admission():
    # Arrange
    ref = next(ref for ref in discover_api_plugins() if ref.name == "scitex-sdk")
    admission = admit(ref, review_ref="owned-test", enabled=())
    # Act
    # Assert
    with pytest.raises(AdmissionDenied, match="not enabled"):
        resolve_handler(ref, admission, "skills")


def test_admitted_read_route_calls_actual_sdk_view():
    # Arrange
    ref = next(ref for ref in discover_api_plugins() if ref.name == "scitex-sdk")
    admission = admit(ref, review_ref="owned-test", enabled=("skills",))
    # Act
    handler = resolve_handler(ref, admission, "skills")
    response = handler(RequestFactory().get("/unmounted/skills"))
    # Assert
    assert (response.status_code, json.loads(response.content)["package"]) == (
        200,
        "scitex-sdk",
    )


def test_descriptor_exposes_one_public_read_only_operation():
    # Arrange
    route = plugin.routes[0]
    # Act
    fragment = plugin.openapi_fragment()
    # Assert
    assert (
        len(plugin.routes),
        route.read_only,
        route.auth.public,
        route.auth.project_scope,
        set(fragment["paths"]["/skills"]),
    ) == (1, True, True, "none", {"get"})


def test_sdk_source_passes_its_own_quality_rule():
    # Arrange
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    # Act
    findings = scan_web_contract(root)
    # Assert
    assert findings == []
