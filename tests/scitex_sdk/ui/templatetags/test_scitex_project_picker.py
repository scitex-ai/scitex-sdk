#!/usr/bin/env python3
"""{% scitex_project_picker %}: only project-scope apps render a picker."""

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        USE_I18N=True,
        LANGUAGE_CODE="en",
        STATIC_URL="/static/",
        DATABASES={},
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.ui"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
    )
    django.setup()

from django.template import Context, engines  # noqa: E402

PICKER = (
    "{% load scitex_project_picker %}"
    '{% scitex_project_picker provider_url="/api/projects/" current="alice/paper" %}'
)


def _render(context):
    return engines["django"].from_string(PICKER).template.render(Context(context))


def test_user_scope_app_renders_no_picker():
    # Arrange
    context = {"app_scope": "user"}
    # Act
    html = _render(context)
    # Assert
    assert html == ""


def test_app_without_declared_scope_renders_no_picker():
    # Arrange
    context = {}
    # Act
    html = _render(context)
    # Assert
    assert html == ""


def test_project_scope_app_renders_the_picker_mount():
    # Arrange
    context = {"app_scope": "project"}
    # Act
    html = _render(context)
    # Assert
    assert 'data-stx-project-picker data-provider-url="/api/projects/"' in html


def test_project_scope_picker_carries_the_explicit_project():
    # Arrange
    context = {"app_scope": "project"}
    # Act
    html = _render(context)
    # Assert
    assert 'data-current="alice/paper"' in html


class _Project:
    slug = "paper"


class HostProvider:
    def project_id(self, project):
        return f"host/{project.slug}"


def _render_source(source, context):
    return engines["django"].from_string(source).template.render(Context(context))


def test_picker_defaults_to_the_host_registered_provider():
    # Arrange
    from django.test import override_settings

    source = '{% load scitex_project_picker %}{% scitex_project_picker scope="project" %}'
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/host/projects/"):
        html = _render_source(source, {})
    # Assert
    assert 'data-provider-url="/host/projects/"' in html


def test_picker_without_any_provider_renders_nothing():
    # Arrange
    source = '{% load scitex_project_picker %}{% scitex_project_picker scope="project" %}'
    # Act
    html = _render_source(source, {})
    # Assert
    assert html == ""


def test_picker_maps_a_project_object_through_the_host_provider():
    # Arrange
    from django.test import override_settings

    source = (
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker scope="project" current=project %}'
    )
    host = {
        "SCITEX_PROJECT_PROVIDER_URL": "/host/projects/",
        "SCITEX_PROJECT_PROVIDER": f"{__name__}.HostProvider",
    }
    # Act
    with override_settings(**host):
        html = _render_source(source, {"project": _Project()})
    # Assert
    assert 'data-current="host/paper"' in html


def test_provider_meta_advertises_the_host_endpoint():
    # Arrange
    from types import SimpleNamespace

    from django.test import override_settings

    source = "{% load scitex_project_picker %}{% scitex_project_provider_meta %}"
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/host/projects/"):
        html = _render_source(source, {"request": request})
    # Assert
    assert html == '<meta name="stx-project-provider" content="/host/projects/">'


def test_provider_meta_is_absent_for_anonymous_visitors():
    # Arrange
    from types import SimpleNamespace

    from django.test import override_settings

    source = "{% load scitex_project_picker %}{% scitex_project_provider_meta %}"
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/host/projects/"):
        html = _render_source(source, {"request": request})
    # Assert
    assert html == ""


def test_unknown_scope_fails_loud():
    # Arrange
    context = {"app_scope": "projcet"}
    # Act
    render = lambda: _render(context)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        render()


# EOF
