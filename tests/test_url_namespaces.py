"""Real Django reverse/resolve/client consumers of namespace aliases."""
import types
import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.test import Client, override_settings
from django.urls import include, path, resolve, reverse
from scitex_sdk.urls import NamespaceCollision, mount_urlpatterns

if not settings.configured:
    settings.configure(SECRET_KEY="namespace-tests",ALLOWED_HOSTS=["testserver"],DATABASES={})

def leaf(aliases=("previous",)):
    module=types.ModuleType("synthetic_leaf")
    module.app_name="current"
    module.namespace_aliases=aliases
    def view(request,item):
        return JsonResponse({"item":item,"method":request.method})
    module.urlpatterns=[path("items/<int:item>/",view,name="item")]
    return module

def _mounted(prefix):
    module=leaf()
    root=types.ModuleType("namespace_root")
    root.urlpatterns=mount_urlpatterns(prefix,module)
    return module,root

@pytest.mark.parametrize("prefix",["","custom/plot/","apps/synthetic/"])
def test_canonical_and_legacy_reverse_reach_identical_view(prefix):
    # Arrange
    module,root=_mounted(prefix)
    # Act
    with override_settings(ROOT_URLCONF=root):
        urls=[reverse(name+":item",kwargs={"item":7}) for name in ("current","previous")]
    # Assert
    assert urls==["/"+prefix+"items/7/"]*2

@pytest.mark.parametrize("prefix",["","custom/plot/","apps/synthetic/"])
def test_canonical_and_legacy_resolve_reaches_the_leaf_view(prefix):
    # Arrange
    module,root=_mounted(prefix)
    # Act
    with override_settings(ROOT_URLCONF=root):
        urls=[reverse(name+":item",kwargs={"item":7}) for name in ("current","previous")]
        target=resolve(urls[0])
    # Assert
    assert target.func is module.urlpatterns[0].callback

@pytest.mark.parametrize("prefix",["","custom/plot/","apps/synthetic/"])
def test_legacy_alias_serves_get_with_item_payload(prefix):
    # Arrange
    module,root=_mounted(prefix)
    # Act
    with override_settings(ROOT_URLCONF=root):
        urls=[reverse(name+":item",kwargs={"item":7}) for name in ("current","previous")]
        payload=Client().get(urls[1]).json()
    # Assert
    assert payload=={"item":7,"method":"GET"}

@pytest.mark.parametrize("prefix",["","custom/plot/","apps/synthetic/"])
def test_canonical_name_serves_post_with_item_payload(prefix):
    # Arrange
    module,root=_mounted(prefix)
    # Act
    with override_settings(ROOT_URLCONF=root):
        urls=[reverse(name+":item",kwargs={"item":7}) for name in ("current","previous")]
        payload=Client().post(urls[0]).json()
    # Assert
    assert payload=={"item":7,"method":"POST"}

@pytest.mark.parametrize("instance",["alternate","previous"])
def test_explicit_instance_preserves_application_and_legacy_names(instance):
    # Arrange
    root=types.ModuleType("instance_root")
    root.urlpatterns=mount_urlpatterns("chosen/",leaf(),namespace=instance)
    # Act
    names=("current",instance,"previous")
    # Assert
    with override_settings(ROOT_URLCONF=root):
        for name in names:
            assert reverse(name+":item",kwargs={"item":2})=="/chosen/items/2/"

@pytest.mark.parametrize("aliases",[None,False,"old",[""],["old:name"],["/old"],["old name"],[1],["old","old"],["current"]])
def test_invalid_aliases_fail_before_a_mount_is_returned(aliases):
    # Arrange
    target=leaf(aliases)
    # Act
    # Assert
    with pytest.raises(ImproperlyConfigured):
        mount_urlpatterns("apps/x/",target)

def test_alias_requires_an_application_namespace():
    # Arrange
    module=leaf()
    del module.app_name
    # Act
    # Assert
    with pytest.raises(ImproperlyConfigured):
        mount_urlpatterns("",module)

def _shadowed_existing(nested):
    # Arrange helper — a pre-existing "other"-namespaced include,
    # optionally nested one level deeper.
    existing = [path("elsewhere/", include(([path("", lambda r: None)], "other"), namespace="previous"))]
    if nested:
        return [path("group/", include(existing))]
    return existing


def test_other_namespace_owner_cannot_be_shadowed_flat():
    # Arrange
    existing = _shadowed_existing(False)
    # Act
    # Assert
    with pytest.raises(NamespaceCollision):
        mount_urlpatterns("apps/new/", leaf(), existing=existing)


def test_other_namespace_owner_cannot_be_shadowed_nested():
    # Arrange
    existing = _shadowed_existing(True)
    # Act
    # Assert
    with pytest.raises(NamespaceCollision):
        mount_urlpatterns("apps/new/", leaf(), existing=existing)

def test_namespaces_inside_a_different_named_parent_are_a_separate_scope():
    # Arrange
    child=[path("",include(([path("",lambda r:None)],"other"),namespace="previous"))]
    existing=[path("elsewhere/",include((child,"outer"),namespace="outer"))]
    # Act
    mounted=mount_urlpatterns("apps/new/",leaf(),existing=existing)
    # Assert
    assert len(mounted)==2

def test_alias_cannot_be_hidden_by_an_existing_application_namespace():
    # Arrange
    existing=[path("elsewhere/",include(([path("",lambda r:None)],"previous"),namespace="custom-other"))]
    # Act
    # Assert
    with pytest.raises(NamespaceCollision):
        mount_urlpatterns("apps/new/",leaf(),existing=existing)

def test_application_namespace_without_aliases_keeps_django_include_behavior():
    # Arrange
    module=leaf(())
    root=types.ModuleType("unchanged_root")
    # Act
    root.urlpatterns=mount_urlpatterns("same/",module)
    # Assert
    with override_settings(ROOT_URLCONF=root):
        assert reverse("current:item",kwargs={"item":1})=="/same/items/1/"
