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


def test_picker_without_any_provider_renders_empty_slot():
    # Arrange — project scope, signed in (no request), no provider
    # anywhere: the tag degrades gracefully, never raises (cross-app
    # adoption rule, amended 2026-10-24).
    source = '{% load scitex_project_picker %}{% scitex_project_picker scope="project" %}'
    # Act
    html = _render_source(source, {})
    # Assert
    assert html == ""


def test_picker_without_any_provider_is_loud_only_when_strict():
    # Arrange — same provider-less render with the explicit strict flag:
    # opting into strict restores the loud failure.
    from django.core.exceptions import ImproperlyConfigured

    source = '{% load scitex_project_picker %}{% scitex_project_picker scope="project" strict=True %}'
    # Act
    # Assert
    with pytest.raises(ImproperlyConfigured, match="no provider"):
        _render_source(source, {})


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


@pytest.mark.parametrize("capability", [None, False, "true", 1])
def test_user_scope_capability_requires_explicit_boolean(capability):
    # Arrange
    source = (
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker provider_url="/api/projects/" allow_user_scope=capability %}'
    )
    context = {"app_scope": "user", "capability": capability}
    # Act
    html = _render_source(source, context)
    # Assert
    assert html == ""


def test_enabled_user_scope_tag_carries_explicit_capability_and_current_scope():
    # Arrange
    source = (
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker provider_url="/api/projects/" allow_user_scope=True current_scope="user" %}'
    )
    context = {"app_scope": "user"}
    # Act
    html = _render_source(source, context)
    # Assert
    assert 'data-allow-user-scope="true" data-current-scope="user"' in html


def test_disabled_project_capability_is_byte_identical_to_omitted():
    # Arrange
    source = (
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker provider_url="/api/projects/" current="alice/paper" allow_user_scope=False %}'
    )
    context = {"app_scope": "project"}
    # Act
    actual, expected = _render_source(source, context), _render(context)
    # Assert
    assert actual == expected


def test_enabled_picker_still_requires_signed_in_user():
    # Arrange
    from types import SimpleNamespace

    source = (
        "{% load scitex_project_picker %}"
        '{% scitex_project_picker provider_url="/api/projects/" allow_user_scope=True %}'
    )
    context = {"app_scope": "user", "request": SimpleNamespace(user=SimpleNamespace(is_authenticated=False))}
    # Act
    html = _render_source(source, context)
    # Assert
    assert html == ""


def test_enabled_picker_without_provider_renders_empty_slot():
    # Arrange — user scope opted in, signed in, still no provider:
    # opting in does not opt out of graceful degradation.
    source = "{% load scitex_project_picker %}{% scitex_project_picker allow_user_scope=True %}"
    # Act
    html = _render_source(source, {"app_scope": "user"})
    # Assert
    assert html == ""


def test_enabled_picker_without_provider_is_loud_only_when_strict():
    # Arrange — user scope opted in with the explicit strict flag:
    # strict restores the loud failure for the provider-less render.
    from django.core.exceptions import ImproperlyConfigured

    source = "{% load scitex_project_picker %}{% scitex_project_picker allow_user_scope=True strict=True %}"
    # Act
    # Assert
    with pytest.raises(ImproperlyConfigured, match="no provider"):
        _render_source(source, {"app_scope": "user"})


@pytest.mark.parametrize(
    "opening,closing,autoescape",
    [("", "", False), ("{% autoescape off %}", "{% endautoescape %}", True)],
)
def test_picker_fragment_preserves_escaping_when_caller_disables_it(
    opening, closing, autoescape
):
    # Arrange
    page = engines["django"].from_string(
        opening + "{% load scitex_project_picker %}"
        '{% scitex_project_picker scope="project" provider_url=endpoint placeholder=hint %}'
        + closing
    )
    context = Context(
        {"endpoint": '/api" data-probe="injected', "hint": "<b>placeholder</b>"},
        autoescape=autoescape,
    )
    # Act
    html = page.template.render(context)
    # Assert
    assert (
        'data-provider-url="/api&quot; data-probe=&quot;injected"' in html
        and 'data-placeholder="&lt;b&gt;placeholder&lt;/b&gt;"' in html
        and 'data-probe="injected"' not in html
    )


def test_direct_picker_helper_keeps_standalone_rendering_without_active_template():
    # Arrange
    from scitex_sdk.ui.templatetags.scitex_project_picker import scitex_project_picker

    context = Context({"app_scope": "project"})
    expected = _render({"app_scope": "project"})
    # Act
    html = scitex_project_picker(
        context, provider_url="/api/projects/", current="alice/paper"
    )
    # Assert
    assert html == expected and context.template is None


# EOF


class AppContextProvider:
    """Real host protocol implementation with an optional contextual URL hook."""

    def list_projects(self, request):
        return []

    def last_visited(self, request):
        return None

    def remember(self, request, project_id):
        raise ValueError("no projects")

    def current_scope(self, request):
        return None

    def remember_scope(self, request, selection):
        raise ValueError("no selection")

    def project_provider_url(self, request, base_url):
        return base_url + "?app=" + request.path_info.split("/")[2]


def test_host_context_reaches_explicit_picker_and_canonical_meta():
    # Arrange
    from django.test import RequestFactory, override_settings
    request = RequestFactory().get("/apps/writer/")
    from types import SimpleNamespace
    request.user = SimpleNamespace(is_authenticated=True)
    source = ("{% load scitex_project_picker %}{% scitex_project_provider_meta %}"
              '{% scitex_project_picker scope="project" provider_url="/host/projects/" %}')
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/host/projects/",
                           SCITEX_PROJECT_PROVIDER=f"{__name__}.AppContextProvider"):
        html = _render_source(source, {"request": request})
    # Assert
    assert ('content="/host/projects/?app=writer"' in html
            and 'data-provider-url="/host/projects/?app=writer"' in html
            and 'data-allow-user-scope="true"' in html
            and 'data-scoped-protocol="true"' in html)


def test_provider_url_without_request_remains_legacy_compatible():
    # Arrange
    from django.test import override_settings
    from scitex_sdk.ui.project_scope import host_project_provider_url
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER_URL="/host/projects/",
                           SCITEX_PROJECT_PROVIDER=f"{__name__}.AppContextProvider"):
        url = host_project_provider_url()
    # Assert
    assert url == "/host/projects/"


def test_picker_assets_have_content_versions():
    # Arrange
    import re
    # Act
    html = _render({"app_scope": "project"})
    # Assert
    assert all(re.search(r"project-selector\." + ext + r"\?v=[a-f0-9]+", html)
               for ext in ("css", "js"))
