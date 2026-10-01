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

@pytest.mark.parametrize("prefix",["","custom/plot/","apps/synthetic/"])
def test_canonical_and_legacy_reverse_reach_identical_view(prefix):
    module=leaf();root=types.ModuleType("namespace_root")
    root.urlpatterns=mount_urlpatterns(prefix,module)
    with override_settings(ROOT_URLCONF=root):
        urls=[reverse(name+":item",kwargs={"item":7}) for name in ("current","previous")]
        assert urls==["/"+prefix+"items/7/"]*2
        assert resolve(urls[0]).func is module.urlpatterns[0].callback
        assert Client().get(urls[1]).json()=={"item":7,"method":"GET"}
        assert Client().post(urls[0]).json()=={"item":7,"method":"POST"}

@pytest.mark.parametrize("instance",["alternate","previous"])
def test_explicit_instance_preserves_application_and_legacy_names(instance):
    root=types.ModuleType("instance_root")
    root.urlpatterns=mount_urlpatterns("chosen/",leaf(),namespace=instance)
    with override_settings(ROOT_URLCONF=root):
        for name in ("current",instance,"previous"):
            assert reverse(name+":item",kwargs={"item":2})=="/chosen/items/2/"

@pytest.mark.parametrize("aliases",[None,False,"old",[""],["old:name"],["/old"],["old name"],[1],["old","old"],["current"]])
def test_invalid_aliases_fail_before_a_mount_is_returned(aliases):
    with pytest.raises(ImproperlyConfigured):mount_urlpatterns("apps/x/",leaf(aliases))

def test_alias_requires_an_application_namespace():
    module=leaf();del module.app_name
    with pytest.raises(ImproperlyConfigured):mount_urlpatterns("",module)

@pytest.mark.parametrize("nested",[False,True])
def test_other_namespace_owner_cannot_be_shadowed(nested):
    existing=[path("elsewhere/",include(([path("",lambda r:None)],"other"),namespace="previous"))]
    if nested:existing=[path("group/",include(existing))]
    with pytest.raises(NamespaceCollision):mount_urlpatterns("apps/new/",leaf(),existing=existing)

def test_namespaces_inside_a_different_named_parent_are_a_separate_scope():
    child=[path("",include(([path("",lambda r:None)],"other"),namespace="previous"))]
    existing=[path("elsewhere/",include((child,"outer"),namespace="outer"))]
    assert len(mount_urlpatterns("apps/new/",leaf(),existing=existing))==2

def test_alias_cannot_be_hidden_by_an_existing_application_namespace():
    existing=[path("elsewhere/",include(([path("",lambda r:None)],"previous"),namespace="custom-other"))]
    with pytest.raises(NamespaceCollision):mount_urlpatterns("apps/new/",leaf(),existing=existing)

def test_application_namespace_without_aliases_keeps_django_include_behavior():
    module=leaf(());root=types.ModuleType("unchanged_root")
    root.urlpatterns=mount_urlpatterns("same/",module)
    with override_settings(ROOT_URLCONF=root):assert reverse("current:item",kwargs={"item":1})=="/same/items/1/"
